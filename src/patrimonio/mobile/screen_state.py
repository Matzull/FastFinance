"""Pure state and formatting helpers for mobile screens."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MobileRequestState:
    """Tracks loading/success/error state for a screen section."""

    loading: bool = False
    message: str = ""

    def set_loading(self, message: str) -> None:
        self.loading = True
        self.message = message

    def set_success(self, message: str) -> None:
        self.loading = False
        self.message = message

    def set_error(self, message: str) -> None:
        self.loading = False
        self.message = message


def format_bank_lines(banks: list[dict]) -> list[str]:
    lines: list[str] = []
    for bank in banks:
        bank_id = bank.get("id", "-")
        name = bank.get("nombre", "-")
        balance = bank.get("saldo_actual", "0")
        lines.append(f"#{bank_id} - {name}: {balance}")
    return lines


def format_transaction_lines(transactions: list[dict], limit: int = 10) -> list[str]:
    lines: list[str] = []
    for txn in transactions[:limit]:
        txn_id = txn.get("id", "-")
        amount = txn.get("cantidad", "0")
        desc = txn.get("descripcion", "")
        category = txn.get("categoria", "")
        lines.append(f"#{txn_id} - {amount} | {desc} ({category})")
    return lines
