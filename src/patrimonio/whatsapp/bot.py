"""WhatsApp adapter for Patrimonio using Twilio credentials."""

import os
from decimal import Decimal

from patrimonio.bot.service import FinanceBotService
from patrimonio.models import TipoTransaccion

(
    WAITING_BANK,
    WAITING_CATEGORY,
    WAITING_CONFIRMATION,
    WAITING_EDIT_FIELD,
    WAITING_EDIT_VALUE,
) = range(5)


class PatrimonioWhatsAppBot:
    """Simple text-first WhatsApp flow adapter."""

    def __init__(self, account_sid: str, auth_token: str, openai_api_key: str | None = None):
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.service = FinanceBotService(openai_api_key=openai_api_key)
        self.user_states: dict[str, dict] = {}

    def get_welcome_message(self) -> str:
        return (
            "🏦 Bienvenido al Bot de Patrimonio\n\n"
            "Comandos: saldo, resumen, gastos, ingresos, suscripciones, patrimonio, bancos\n"
            "Registro manual: gasto <cantidad> <descripcion> | ingreso <cantidad> <descripcion>\n"
            "Para OCR: envia 'foto' con una imagen."
        )

    def process_message(self, user_id: str, text: str, image_bytes: bytes | None = None) -> str:
        command = text.strip().lower()

        if command == "foto" and image_bytes is not None:
            return self._handle_photo(user_id, image_bytes)

        if command == "saldo":
            return self.service.get_balance_message()
        if command == "resumen":
            return self.service.get_monthly_summary_message()
        if command == "gastos":
            return self.service.get_recent_expenses_message()
        if command == "ingresos":
            return self.service.get_recent_income_message()
        if command == "suscripciones":
            return self.service.get_subscriptions_message()
        if command == "patrimonio":
            return self.service.get_net_worth_message()
        if command == "bancos":
            return self.service.get_banks_message() or "❌ No hay cuentas bancarias registradas."

        if command.startswith("gasto "):
            return self._handle_manual_expense(user_id, command[6:])
        if command.startswith("ingreso "):
            return self._handle_manual_income(user_id, command[8:])

        state = self.user_states.get(user_id, {}).get("state")
        if state == WAITING_EDIT_FIELD:
            return self._handle_edit_menu(user_id, command)
        if state == WAITING_EDIT_VALUE:
            return self._handle_edit_value(user_id, text.strip())
        if state == WAITING_BANK:
            return self._handle_bank_selection(user_id, command)
        if state == WAITING_CATEGORY:
            return self._handle_category_selection(user_id, command)
        if state == WAITING_CONFIRMATION:
            return self._handle_confirmation(user_id, command)

        return "❌ Comando no reconocido. Escribe 'saldo', 'resumen', 'gasto ...' o 'foto'."

    def _handle_photo(self, user_id: str, image_bytes: bytes) -> str:
        message, error = self.service.process_receipt_image(user_id, image_bytes)
        if error:
            return message
        self.user_states[user_id] = {"state": WAITING_EDIT_FIELD}
        return f"{message}\n\nResponde: editar | confirmar"

    def _handle_manual_expense(self, user_id: str, payload: str) -> str:
        parts = payload.split(None, 1)
        if len(parts) < 2:
            return "❌ Formato: gasto <cantidad> <descripcion>"
        try:
            amount = Decimal(parts[0].replace(",", "."))
        except Exception:
            return "❌ Cantidad invalida."
        error = self.service.create_manual_expense(user_id, amount, parts[1])
        if error:
            return error
        self.user_states[user_id] = {"state": WAITING_BANK}
        return self._render_bank_options()

    def _handle_manual_income(self, user_id: str, payload: str) -> str:
        parts = payload.split(None, 1)
        if len(parts) < 2:
            return "❌ Formato: ingreso <cantidad> <descripcion>"
        try:
            amount = Decimal(parts[0].replace(",", "."))
        except Exception:
            return "❌ Cantidad invalida."
        error = self.service.create_manual_income(user_id, amount, parts[1])
        if error:
            return error
        self.user_states[user_id] = {"state": WAITING_BANK}
        return self._render_bank_options()

    def _handle_edit_menu(self, user_id: str, command: str) -> str:
        if command == "confirmar":
            self.user_states[user_id] = {"state": WAITING_BANK}
            return self._render_bank_options()
        if command != "editar":
            return "❌ Responde con 'editar' o 'confirmar'."

        data = self.service.get_editable_data_dict(user_id)
        if not data:
            return "❌ No hay datos en edicion."
        options = ["amount", "date", "merchant", "description"]
        self.user_states[user_id] = {"state": WAITING_EDIT_VALUE, "fields": options}
        return "Campos editables: amount, date, merchant, description. Ejemplo: amount=12.50"

    def _handle_edit_value(self, user_id: str, text: str) -> str:
        if "=" not in text:
            return "❌ Formato invalido. Usa campo=valor"
        field, value = (part.strip() for part in text.split("=", 1))
        error, emoji, rendered = self.service.update_field(user_id, field, value)
        if error:
            return error
        self.user_states[user_id] = {"state": WAITING_EDIT_FIELD}
        summary = self.service.get_editable_data_message(user_id)
        return f"{emoji} ✅ Actualizado: {rendered}\n\n{summary}\n\nResponde: editar | confirmar"

    def _render_bank_options(self) -> str:
        banks = self.service.list_banks()
        if not banks:
            return "❌ No hay cuentas bancarias registradas."
        lines = ["🏦 Selecciona una cuenta:"]
        for index, bank in enumerate(banks, start=1):
            lines.append(f"{index}. {bank.nombre}")
        return "\n".join(lines)

    def _handle_bank_selection(self, user_id: str, text: str) -> str:
        banks = self.service.list_banks()
        try:
            choice = int(text)
            bank = banks[choice - 1]
        except Exception:
            return f"❌ Opcion invalida. Elige un numero entre 1 y {len(banks)}"

        error = self.service.set_bank(user_id, bank.id)
        if error:
            return error
        data = self.service.get_editable_data_dict(user_id)
        categories = self.service.list_categories(data["transaction_type"] == TipoTransaccion.GASTO)
        self.user_states[user_id] = {"state": WAITING_CATEGORY}
        lines = ["📂 Selecciona categoria:"]
        for index, category in enumerate(categories, start=1):
            lines.append(f"{index}. {category.value}")
        return "\n".join(lines)

    def _handle_category_selection(self, user_id: str, text: str) -> str:
        data = self.service.get_editable_data_dict(user_id)
        categories = self.service.list_categories(data["transaction_type"] == TipoTransaccion.GASTO)
        try:
            category = categories[int(text) - 1].value
        except Exception:
            return f"❌ Opcion invalida. Elige un numero entre 1 y {len(categories)}"
        error = self.service.set_category(user_id, category)
        if error:
            return error
        self.user_states[user_id] = {"state": WAITING_CONFIRMATION}
        return f"{self.service.get_confirmation_message(user_id)}\n\nResponde: si | no"

    def _handle_confirmation(self, user_id: str, text: str) -> str:
        if text in {"si", "sí", "yes"}:
            ok, message = self.service.confirm_transaction(user_id)
            self.user_states.pop(user_id, None)
            return message if ok else message
        if text in {"no", "cancelar"}:
            self.service.cancel_flow(user_id)
            self.user_states.pop(user_id, None)
            return "❌ Operacion cancelada."
        return "❌ Responde con 'si' o 'no'."


def main() -> None:
    from dotenv import load_dotenv

    load_dotenv()
    account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
    if not account_sid or not auth_token:
        print("❌ Error: Define TWILIO_ACCOUNT_SID y TWILIO_AUTH_TOKEN")
        return
    PatrimonioWhatsAppBot(
        account_sid=account_sid,
        auth_token=auth_token,
        openai_api_key=os.environ.get("OPENAI_API_KEY"),
    )
    print("✅ Bot de WhatsApp inicializado")


if __name__ == "__main__":
    main()
