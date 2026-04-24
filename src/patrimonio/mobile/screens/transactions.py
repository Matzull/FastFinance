"""Transactions screen with visual layout."""

from __future__ import annotations

from kivy.app import App
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView

from patrimonio.mobile.async_requests import run_background
from patrimonio.mobile.md_compat import (
    body_label,
    box_layout,
    button,
    card_container,
    notify,
    status_label,
    text_field,
    title_label,
)
from patrimonio.mobile.screen_state import format_transaction_lines


class TransactionsScreen(Screen):
    """Lists and manages transactions with visual hierarchy."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        root = box_layout(orientation="vertical", spacing=10, padding=12)
        self.status_label = status_label("No data loaded")
        self.items_label = body_label("")

        self.bank_id_input = text_field("Bank ID", numeric=True)
        self.type_input = text_field("Type: ingreso or gasto", text="gasto")
        self.amount_input = text_field("Amount")
        self.description_input = text_field("Description")
        self.category_input = text_field("Category", text="otros")
        self.delete_id_input = text_field("Transaction ID to delete", numeric=True)

        create_btn = button("Create transaction")
        create_btn.bind(on_release=lambda *_: self.create_transaction())
        delete_btn = button("Delete transaction", outlined=True)
        delete_btn.bind(on_release=lambda *_: self.delete_transaction())
        refresh_btn = button("Refresh transactions")
        refresh_btn.bind(on_release=lambda *_: self.refresh())

        content = box_layout(orientation="vertical", spacing=8, size_hint_y=None)
        content.bind(minimum_height=content.setter("height"))

        list_card = card_container()
        list_card.add_widget(title_label("Latest transactions"))
        list_card.add_widget(self.status_label)
        list_card.add_widget(self.items_label)
        list_card.add_widget(refresh_btn)
        content.add_widget(list_card)

        form_card = card_container()
        form_card.add_widget(title_label("New transaction"))
        form_card.add_widget(self.bank_id_input)
        form_card.add_widget(self.type_input)
        form_card.add_widget(self.amount_input)
        form_card.add_widget(self.description_input)
        form_card.add_widget(self.category_input)
        form_card.add_widget(create_btn)
        content.add_widget(form_card)

        delete_card = card_container()
        delete_card.add_widget(title_label("Manage transactions"))
        delete_card.add_widget(self.delete_id_input)
        delete_card.add_widget(delete_btn)
        content.add_widget(delete_card)

        scroll = ScrollView(size_hint=(1, 1))
        scroll.add_widget(content)
        root.add_widget(scroll)
        self.add_widget(root)

    def refresh(self) -> None:
        self.status_label.text = "Loading transactions..."

        def work():
            app = App.get_running_app()
            return app.api_client.list_transactions(limit=20)

        def on_success(txns):
            if not txns:
                self.status_label.text = "No transactions found"
                self.items_label.text = ""
                return
            lines = format_transaction_lines(txns, limit=10)
            self.items_label.text = "\n".join(lines)
            self.status_label.text = f"Loaded {len(txns)} transactions"

        def on_error(exc: Exception):
            self.status_label.text = f"Error: {exc}"

        run_background(work, on_success, on_error)

    def create_transaction(self) -> None:
        if not self.bank_id_input.text.strip():
            self.status_label.text = "Bank ID is required"
            return
        if not self.amount_input.text.strip():
            self.status_label.text = "Amount is required"
            return
        payload = {
            "banco_id": int(self.bank_id_input.text.strip()),
            "tipo": self.type_input.text.strip().lower() or "gasto",
            "cantidad": self.amount_input.text.strip(),
            "descripcion": self.description_input.text.strip() or "Mobile transaction",
            "categoria": self.category_input.text.strip() or "otros",
            "fecha": None,
            "notas": None,
        }
        self.status_label.text = "Creating transaction..."

        def work():
            app = App.get_running_app()
            return app.api_client.create_transaction(payload)

        def on_success(_txn):
            self.status_label.text = "Transaction created"
            notify("Transaction created")
            self.amount_input.text = ""
            self.description_input.text = ""
            self.refresh()

        def on_error(exc: Exception):
            self.status_label.text = f"Error: {exc}"
            notify(f"Create failed: {exc}")

        run_background(work, on_success, on_error)

    def delete_transaction(self) -> None:
        raw_id = self.delete_id_input.text.strip()
        if not raw_id:
            self.status_label.text = "Transaction ID is required"
            return
        transaction_id = int(raw_id)
        self.status_label.text = "Deleting transaction..."

        def work():
            app = App.get_running_app()
            return app.api_client.delete_transaction(transaction_id)

        def on_success(_result):
            self.status_label.text = "Transaction deleted"
            notify("Transaction deleted")
            self.delete_id_input.text = ""
            self.refresh()

        def on_error(exc: Exception):
            self.status_label.text = f"Error: {exc}"
            notify(f"Delete failed: {exc}")

        run_background(work, on_success, on_error)
