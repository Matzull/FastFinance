"""Channel-agnostic business logic for finance bots."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from patrimonio.database import GestorDB
from patrimonio.models import CategoriaGasto, CategoriaIngreso, TipoTransaccion
from patrimonio.telegram.ocr import ReceiptExtractor


@dataclass
class TicketData:
    """In-memory data for one pending transaction flow."""

    transaction_type: TipoTransaccion
    amount: Decimal | None = None
    description: str | None = None
    txn_date: date | None = None
    merchant: str | None = None
    bank_id: int | None = None
    category: str | None = None


class FinanceBotService:
    """Shared service used by Telegram and WhatsApp adapters."""

    def __init__(self, openai_api_key: str | None = None):
        self.db = GestorDB()
        self.ocr_extractor = ReceiptExtractor(openai_api_key=openai_api_key)
        self.pending_data: dict[int | str, TicketData] = {}

    def get_balance_message(self) -> str:
        banks = self.db.list_banks()
        if not banks:
            return "❌ No accounts registered."

        total = Decimal("0")
        message = "💰 *Current balances:*\n\n"
        for bank in banks:
            balance = self.db.calculate_bank_balance(bank.id)
            total += balance
            sign = "🟢" if balance >= 0 else "🔴"
            message += f"{sign} {bank.nombre}: *{balance:,.2f}€*\n"
        return message + f"\n📊 *Total: {total:,.2f}€*"

    def get_banks_message(self) -> str | None:
        banks = self.db.list_banks()
        if not banks:
            return None

        message = "🏦 *Your bank accounts:*\n\n"
        for bank in banks:
            balance = self.db.calculate_bank_balance(bank.id)
            emoji = "💳" if bank.tipo_cuenta == "corriente" else "💰"
            message += f"{emoji} *{bank.nombre}*\n"
            message += f"   Type: {bank.tipo_cuenta}\n"
            message += f"   Balance: {balance:,.2f} {bank.moneda}\n\n"
        return message

    def get_monthly_summary_message(self) -> str:
        today = date.today()
        summary = self.db.monthly_summary(today.year, today.month)
        sub_cost = self.db.calculate_monthly_subscription_cost()
        message = f"📊 *Summary for {today.strftime('%B %Y')}*\n\n"
        message += f"💵 Income: *+{summary['ingresos']:,.2f}€*\n"
        message += f"💸 Expenses: *-{summary['gastos']:,.2f}€*\n"
        message += f"📅 Subscriptions: *-{sub_cost:,.2f}€*/month\n"
        message += f"\n💰 Balance: *{summary['balance']:,.2f}€*"
        return message + (" ✅" if summary["balance"] >= 0 else " ⚠️")

    def get_recent_expenses_message(self, limit: int = 10) -> str:
        txns = self.db.list_transactions(tipo=TipoTransaccion.GASTO, limite=limit)
        if not txns:
            return "📭 No expenses registered."
        message = "💸 *Recent expenses:*\n\n"
        for txn in txns:
            message += f"• {txn.fecha.strftime('%d/%m')} | *{txn.cantidad:,.2f}€* - {txn.descripcion}\n"
            message += f"  _{txn.categoria}_\n"
        return message

    def get_recent_income_message(self, limit: int = 10) -> str:
        txns = self.db.list_transactions(tipo=TipoTransaccion.INGRESO, limite=limit)
        if not txns:
            return "📭 No income entries registered."
        message = "💵 *Recent income:*\n\n"
        for txn in txns:
            message += f"• {txn.fecha.strftime('%d/%m')} | *{txn.cantidad:,.2f}€* - {txn.descripcion}\n"
            message += f"  _{txn.categoria}_\n"
        return message

    def get_subscriptions_message(self) -> str:
        subscriptions = self.db.list_subscriptions(solo_activas=True)
        if not subscriptions:
            return "📭 No active subscriptions."
        monthly_total = Decimal("0")
        message = "📅 *Active subscriptions:*\n\n"
        for subscription in subscriptions:
            monthly_cost = subscription.costo_mensual()
            monthly_total += monthly_cost
            message += f"• *{subscription.nombre}*\n"
            message += f"  {subscription.cantidad:,.2f}€/{subscription.frecuencia.value} (~{monthly_cost:,.2f}€/mes)\n"
        return message + f"\n💰 *Monthly total: {monthly_total:,.2f}€*"

    def get_net_worth_message(self) -> str:
        result = self.db.calculate_net_worth()
        message = "🏛️ *Your Net Worth*\n\n"
        message += f"📈 Assets: *+{result['activos']:,.2f}€*\n"
        message += f"📉 Liabilities: *-{result['pasivos']:,.2f}€*\n"
        message += f"\n💎 *Net worth: {result['neto']:,.2f}€*"
        return message + (" 🎉" if result["neto"] >= 0 else "")

    def process_receipt_image(
        self, user_id: int | str, image_bytes: bytes
    ) -> tuple[str, str | None]:
        data = self.ocr_extractor.extract(image_bytes)
        if data.confidence < 0.3:
            message = (
                "❌ I could not read the receipt clearly.\n"
                "Use /gasto <amount> <description> to register it manually.\n"
                f"🔍 Extracted data: {data}"
            )
            return message, "low_confidence"

        self.pending_data[user_id] = TicketData(
            transaction_type=TipoTransaccion.GASTO,
            amount=data.total,
            description=data.description or data.merchant or "Purchase",
            txn_date=data.date or date.today(),
            merchant=data.merchant,
        )
        return self.get_editable_data_message(user_id) + "\n\nIs this correct?", None

    def create_manual_expense(
        self, user_id: int | str, amount: Decimal, description: str
    ) -> str | None:
        if not amount or not description:
            return "❌ Amount and description are required."
        self.pending_data[user_id] = TicketData(
            transaction_type=TipoTransaccion.GASTO,
            amount=amount,
            description=description,
            txn_date=date.today(),
        )
        return None

    def create_manual_income(
        self, user_id: int | str, amount: Decimal, description: str
    ) -> str | None:
        if not amount or not description:
            return "❌ Amount and description are required."
        self.pending_data[user_id] = TicketData(
            transaction_type=TipoTransaccion.INGRESO,
            amount=amount,
            description=description,
            txn_date=date.today(),
        )
        return None

    def get_editable_data_dict(self, user_id: int | str) -> dict[str, Any] | None:
        data = self.pending_data.get(user_id)
        if not data:
            return None
        return {
            "transaction_type": data.transaction_type,
            "amount": data.amount,
            "description": data.description,
            "date": data.txn_date,
            "merchant": data.merchant,
            "bank_id": data.bank_id,
            "category": data.category,
        }

    def get_editable_data_message(self, user_id: int | str) -> str | None:
        data = self.pending_data.get(user_id)
        if not data:
            return None
        message = "📄 *Receipt data:*\n\n"
        if data.amount is not None:
            message += f"💰 Total: *{data.amount:,.2f}€*\n"
        if data.txn_date is not None:
            message += f"📅 Date: {data.txn_date}\n"
        if data.merchant:
            message += f"🏪 Merchant: {data.merchant}\n"
        if data.description:
            message += f"📝 Description: {data.description}\n"
        return message

    def update_field(
        self, user_id: int | str, field: str, value: str
    ) -> tuple[str | None, str, str]:
        data = self.pending_data.get(user_id)
        if not data:
            return "❌ No data is currently being edited.", "", ""
        try:
            if field == "amount":
                parsed = Decimal(value.replace(",", "."))
                data.amount = parsed
                return None, "💰", f"{parsed:,.2f}€"
            if field == "date":
                day, month, year = (int(part) for part in value.split("/"))
                parsed_date = date(year, month, day)
                data.txn_date = parsed_date
                return None, "📅", parsed_date.isoformat()
            if field == "merchant":
                data.merchant = value[:50]
                return None, "🏪", data.merchant
            if field == "description":
                data.description = value[:100]
                return None, "📝", data.description
            return "❌ Unknown field.", "", ""
        except (ValueError, TypeError):
            return "❌ Invalid value.", "", ""

    def list_banks(self) -> list:
        return self.db.list_banks()

    def list_categories(self, is_expense: bool) -> list:
        return list(CategoriaGasto) if is_expense else list(CategoriaIngreso)

    def set_bank(self, user_id: int | str, bank_id: int) -> str | None:
        data = self.pending_data.get(user_id)
        if not data:
            return "❌ No data is currently being edited."
        data.bank_id = bank_id
        return None

    def set_category(self, user_id: int | str, category: str) -> str | None:
        data = self.pending_data.get(user_id)
        if not data:
            return "❌ No data is currently being edited."
        data.category = category
        return None

    def get_confirmation_message(self, user_id: int | str) -> str | None:
        data = self.pending_data.get(user_id)
        if not data or data.bank_id is None or not data.category:
            return None
        bank = self.db.get_bank(data.bank_id)
        kind = (
            "💸 EXPENSE"
            if data.transaction_type == TipoTransaccion.GASTO
            else "💵 INCOME"
        )
        message = f"*{kind}*\n\n"
        message += f"💰 Amount: *{data.amount:,.2f}€*\n"
        message += f"📝 Description: {data.description}\n"
        message += f"📂 Category: {data.category}\n"
        message += f"🏦 Account: {bank.nombre}\n"
        message += f"📅 Date: {data.txn_date}\n\n"
        message += "Confirm?"
        return message

    def confirm_transaction(self, user_id: int | str) -> tuple[bool, str]:
        data = self.pending_data.pop(user_id, None)
        if not data:
            return False, "❌ Error: data not found."
        if (
            data.amount is None
            or data.txn_date is None
            or data.bank_id is None
            or not data.category
        ):
            return False, "❌ Missing required data."
        try:
            self.db.create_transaction(
                tipo=data.transaction_type,
                cantidad=data.amount,
                descripcion=data.description or "",
                categoria=data.category,
                banco_id=data.bank_id,
                fecha=data.txn_date,
            )
            emoji = "💸" if data.transaction_type == TipoTransaccion.GASTO else "💵"
            message = f"✅ {emoji} Transaction registered successfully!\n\n*{data.amount:,.2f}€* - {data.description or ''}"
            return True, message
        except Exception as error:
            return False, f"❌ Save error: {error}"

    def cancel_flow(self, user_id: int | str) -> None:
        self.pending_data.pop(user_id, None)
