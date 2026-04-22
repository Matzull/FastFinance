"""Telegram adapter for Patrimonio finance bot."""

import logging
import os
from decimal import Decimal

import dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from patrimonio.bot.service import FinanceBotService
from patrimonio.models import TipoTransaccion

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

(
    WAITING_BANK,
    WAITING_CATEGORY,
    WAITING_DESCRIPTION,
    WAITING_CONFIRMATION,
    WAITING_MANUAL_AMOUNT,
    WAITING_EDIT_FIELD,
    WAITING_EDIT_VALUE,
) = range(7)


class PatrimonioBot:
    """Telegram bot adapter."""

    def __init__(self, token: str, openai_api_key: str | None = None):
        self.token = token
        self.service = FinanceBotService(openai_api_key=openai_api_key)
        self.user_state: dict[int, int] = {}

        # Backward-compatible public attributes expected by old tests.
        self.db = self.service.db
        self.extractor = self.service.ocr_extractor
        self.pending_data = self.service.pending_data

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        del context
        message = """🏦 *Bienvenido al Bot de Patrimonio*

Soy tu asistente para gestionar tus finanzas.

📸 *Registrar gastos*
• Enviame una foto de un ticket/recibo

📊 *Consultar datos*
• /saldo • /resumen • /gastos • /ingresos
• /suscripciones • /patrimonio • /bancos

💰 *Registro manual*
• /gasto <cantidad> <descripcion>
• /ingreso <cantidad> <descripcion>
"""
        await update.message.reply_text(message, parse_mode="Markdown")

    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await self.start(update, context)

    async def banks(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        del context
        message = self.service.get_banks_message()
        if message is None:
            message = "❌ No tienes cuentas bancarias registradas."
        await update.message.reply_text(message, parse_mode="Markdown")

    async def balance(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        del context
        await update.message.reply_text(
            self.service.get_balance_message(), parse_mode="Markdown"
        )

    async def summary(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        del context
        await update.message.reply_text(
            self.service.get_monthly_summary_message(), parse_mode="Markdown"
        )

    async def expenses(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        del context
        await update.message.reply_text(
            self.service.get_recent_expenses_message(), parse_mode="Markdown"
        )

    async def income(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        del context
        await update.message.reply_text(
            self.service.get_recent_income_message(), parse_mode="Markdown"
        )

    async def subscriptions(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        del context
        await update.message.reply_text(
            self.service.get_subscriptions_message(), parse_mode="Markdown"
        )

    async def net_worth(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        del context
        await update.message.reply_text(
            self.service.get_net_worth_message(), parse_mode="Markdown"
        )

    async def manual_expense(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int | None:
        if not context.args or len(context.args) < 2:
            await update.message.reply_text("❌ Uso: /gasto <cantidad> <descripcion>")
            return None
        try:
            amount = Decimal(context.args[0].replace(",", "."))
        except Exception:
            await update.message.reply_text("❌ Cantidad invalida.")
            return None
        description = " ".join(context.args[1:])
        error = self.service.create_manual_expense(
            update.effective_user.id, amount, description
        )
        if error:
            await update.message.reply_text(error)
            return None
        return await self._ask_bank(update)

    async def manual_income(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int | None:
        if not context.args or len(context.args) < 2:
            await update.message.reply_text("❌ Uso: /ingreso <cantidad> <descripcion>")
            return None
        try:
            amount = Decimal(context.args[0].replace(",", "."))
        except Exception:
            await update.message.reply_text("❌ Cantidad invalida.")
            return None
        description = " ".join(context.args[1:])
        error = self.service.create_manual_income(
            update.effective_user.id, amount, description
        )
        if error:
            await update.message.reply_text(error)
            return None
        return await self._ask_bank(update)

    async def process_photo(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        del context
        await update.message.reply_text("🔍 Analizando ticket...")
        photo = update.message.photo[-1]
        file_obj = await update.get_bot().get_file(photo.file_id)
        image_bytes = await file_obj.download_as_bytearray()

        user_id = update.effective_user.id
        message, error = self.service.process_receipt_image(user_id, bytes(image_bytes))
        if error:
            await update.message.reply_text(message)
            return ConversationHandler.END

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("✏️ Editar", callback_data="edit_ticket"),
                    InlineKeyboardButton(
                        "✅ Confirmar", callback_data="confirm_ticket"
                    ),
                ]
            ]
        )
        await update.message.reply_text(
            message, parse_mode="Markdown", reply_markup=keyboard
        )
        return WAITING_EDIT_FIELD

    async def _ask_bank(self, update: Update) -> int:
        banks = self.service.list_banks()
        if not banks:
            await update.message.reply_text("❌ No hay cuentas bancarias.")
            return ConversationHandler.END
        keyboard = [
            [InlineKeyboardButton(f"🏦 {bank.nombre}", callback_data=f"bank_{bank.id}")]
            for bank in banks
        ]
        keyboard.append([InlineKeyboardButton("❌ Cancelar", callback_data="cancel")])
        await update.message.reply_text(
            "🏦 Selecciona la cuenta:", reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return WAITING_BANK

    async def edit_or_confirm_ticket(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        del context
        query = update.callback_query
        await query.answer()

        if query.data == "confirm_ticket":
            banks = self.service.list_banks()
            if not banks:
                await query.edit_message_text("❌ No hay cuentas bancarias.")
                return ConversationHandler.END
            keyboard = [
                [
                    InlineKeyboardButton(
                        f"🏦 {bank.nombre}", callback_data=f"bank_{bank.id}"
                    )
                ]
                for bank in banks
            ]
            keyboard.append(
                [InlineKeyboardButton("❌ Cancelar", callback_data="cancel")]
            )
            await query.edit_message_text(
                "🏦 Selecciona la cuenta:", reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return WAITING_BANK

        data = self.service.get_editable_data_dict(update.effective_user.id)
        if not data:
            await query.edit_message_text("❌ No hay datos en edicion.")
            return ConversationHandler.END

        keyboard = []
        if data.get("amount") is not None:
            keyboard.append(
                [
                    InlineKeyboardButton(
                        f"💰 Total: {data['amount']:,.2f}€",
                        callback_data="field_amount",
                    )
                ]
            )
        if data.get("date") is not None:
            keyboard.append(
                [
                    InlineKeyboardButton(
                        f"📅 Fecha: {data['date']}", callback_data="field_date"
                    )
                ]
            )
        if data.get("merchant"):
            keyboard.append(
                [
                    InlineKeyboardButton(
                        f"🏪 Comercio: {data['merchant']}",
                        callback_data="field_merchant",
                    )
                ]
            )
        if data.get("description"):
            keyboard.append(
                [
                    InlineKeyboardButton(
                        f"📝 Descripcion: {data['description']}",
                        callback_data="field_description",
                    )
                ]
            )
        keyboard.append(
            [InlineKeyboardButton("← Volver", callback_data="back_to_summary")]
        )
        await query.edit_message_text(
            "✏️ *Que deseas editar?*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return WAITING_EDIT_FIELD

    async def select_edit_field(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        query = update.callback_query
        await query.answer()
        user_id = update.effective_user.id

        if query.data == "back_to_summary":
            message = self.service.get_editable_data_message(user_id)
            keyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("✏️ Editar", callback_data="edit_ticket"),
                        InlineKeyboardButton(
                            "✅ Confirmar", callback_data="confirm_ticket"
                        ),
                    ]
                ]
            )
            await query.edit_message_text(
                f"{message}\n\n¿Es correcto?",
                parse_mode="Markdown",
                reply_markup=keyboard,
            )
            return WAITING_EDIT_FIELD

        field_map = {
            "field_amount": "amount",
            "field_date": "date",
            "field_merchant": "merchant",
            "field_description": "description",
        }
        field_name = field_map.get(query.data)
        if not field_name:
            await query.edit_message_text("❌ Campo invalido.")
            return WAITING_EDIT_FIELD
        context.user_data["edit_field"] = field_name
        prompt_map = {
            "amount": "Escribe el nuevo total:",
            "date": "Escribe la nueva fecha (DD/MM/YYYY):",
            "merchant": "Escribe el nuevo comercio:",
            "description": "Escribe la nueva descripcion:",
        }
        await query.edit_message_text(prompt_map[field_name])
        return WAITING_EDIT_VALUE

    async def process_edit_value(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        user_id = update.effective_user.id
        field_name = context.user_data.get("edit_field")
        if not field_name:
            await update.message.reply_text("❌ Campo invalido.")
            return WAITING_EDIT_VALUE
        error, emoji, rendered = self.service.update_field(
            user_id, field_name, update.message.text.strip()
        )
        if error:
            await update.message.reply_text(error)
            return WAITING_EDIT_VALUE

        summary = self.service.get_editable_data_message(user_id)
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("✏️ Editar", callback_data="edit_ticket"),
                    InlineKeyboardButton(
                        "✅ Confirmar", callback_data="confirm_ticket"
                    ),
                ]
            ]
        )
        await update.message.reply_text(
            f"{emoji} ✅ Actualizado: *{rendered}*", parse_mode="Markdown"
        )
        await update.message.reply_text(
            f"{summary}\n\n¿Es correcto?", parse_mode="Markdown", reply_markup=keyboard
        )
        return WAITING_EDIT_FIELD

    async def select_bank(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        del context
        query = update.callback_query
        await query.answer()

        if query.data == "cancel":
            self.service.cancel_flow(update.effective_user.id)
            await query.edit_message_text("❌ Operacion cancelada.")
            return ConversationHandler.END

        bank_id = int(query.data.replace("bank_", ""))
        error = self.service.set_bank(update.effective_user.id, bank_id)
        if error:
            await query.edit_message_text(error)
            return ConversationHandler.END

        data = self.service.get_editable_data_dict(update.effective_user.id)
        categories = self.service.list_categories(
            data["transaction_type"] == TipoTransaccion.GASTO
        )
        keyboard = []
        row = []
        for category in categories:
            row.append(
                InlineKeyboardButton(
                    category.value.capitalize(), callback_data=f"cat_{category.value}"
                )
            )
            if len(row) == 2:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        keyboard.append([InlineKeyboardButton("❌ Cancelar", callback_data="cancel")])
        await query.edit_message_text(
            "📂 Selecciona la categoria:", reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return WAITING_CATEGORY

    async def select_category(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        del context
        query = update.callback_query
        await query.answer()
        if query.data == "cancel":
            self.service.cancel_flow(update.effective_user.id)
            await query.edit_message_text("❌ Operacion cancelada.")
            return ConversationHandler.END

        error = self.service.set_category(
            update.effective_user.id, query.data.replace("cat_", "")
        )
        if error:
            await query.edit_message_text(error)
            return ConversationHandler.END

        message = self.service.get_confirmation_message(update.effective_user.id)
        if not message:
            await query.edit_message_text("❌ Error: datos incompletos.")
            return ConversationHandler.END
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("✅ Confirmar", callback_data="confirm"),
                    InlineKeyboardButton("❌ Cancelar", callback_data="cancel"),
                ]
            ]
        )
        await query.edit_message_text(
            message, parse_mode="Markdown", reply_markup=keyboard
        )
        return WAITING_CONFIRMATION

    async def confirm_transaction(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        del context
        query = update.callback_query
        await query.answer()
        if query.data == "cancel":
            self.service.cancel_flow(update.effective_user.id)
            await query.edit_message_text("❌ Operacion cancelada.")
            return ConversationHandler.END
        ok, message = self.service.confirm_transaction(update.effective_user.id)
        await query.edit_message_text(message, parse_mode="Markdown" if ok else None)
        return ConversationHandler.END

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        del context
        self.service.cancel_flow(update.effective_user.id)
        await update.message.reply_text("❌ Operacion cancelada.")
        return ConversationHandler.END

    def run(self) -> None:
        app = Application.builder().token(self.token).build()
        conversation = ConversationHandler(
            entry_points=[
                MessageHandler(filters.PHOTO, self.process_photo),
                CommandHandler("gasto", self.manual_expense),
                CommandHandler("ingreso", self.manual_income),
            ],
            states={
                WAITING_EDIT_FIELD: [
                    CallbackQueryHandler(
                        self.select_edit_field,
                        pattern="^field_|^back_to_summary$",
                    ),
                    CallbackQueryHandler(
                        self.edit_or_confirm_ticket,
                        pattern="^edit_ticket$|^confirm_ticket$",
                    ),
                ],
                WAITING_EDIT_VALUE: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND, self.process_edit_value
                    )
                ],
                WAITING_BANK: [
                    CallbackQueryHandler(self.select_bank, pattern="^bank_|^cancel$")
                ],
                WAITING_CATEGORY: [
                    CallbackQueryHandler(self.select_category, pattern="^cat_|^cancel$")
                ],
                WAITING_CONFIRMATION: [
                    CallbackQueryHandler(
                        self.confirm_transaction, pattern="^confirm$|^cancel$"
                    )
                ],
            },
            fallbacks=[CommandHandler("cancelar", self.cancel)],
        )
        app.add_handler(CommandHandler("start", self.start))
        app.add_handler(CommandHandler("ayuda", self.help))
        app.add_handler(CommandHandler("help", self.help))
        app.add_handler(CommandHandler("bancos", self.banks))
        app.add_handler(CommandHandler("saldo", self.balance))
        app.add_handler(CommandHandler("resumen", self.summary))
        app.add_handler(CommandHandler("gastos", self.expenses))
        app.add_handler(CommandHandler("ingresos", self.income))
        app.add_handler(CommandHandler("suscripciones", self.subscriptions))
        app.add_handler(CommandHandler("patrimonio", self.net_worth))
        app.add_handler(conversation)
        logger.info("Telegram bot started")
        app.run_polling(allowed_updates=Update.ALL_TYPES)


def main() -> None:
    dotenv.load_dotenv()
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        print("❌ Error: Define la variable de entorno TELEGRAM_BOT_TOKEN")
        return
    bot = PatrimonioBot(token=token, openai_api_key=os.environ.get("OPENAI_API_KEY"))
    bot.run()


if __name__ == "__main__":
    main()
