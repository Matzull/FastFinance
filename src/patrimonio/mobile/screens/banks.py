"""Banks screen with CRUD actions."""

from __future__ import annotations

from kivy.app import App
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView

from patrimonio.mobile.api_client import ApiClientError
from patrimonio.mobile.async_requests import run_background
from patrimonio.mobile.md_compat import (
    body_label,
    box_layout,
    button,
    card_container,
    status_label,
    text_field,
    title_label,
)
from patrimonio.mobile.screen_state import format_bank_lines


class BanksScreen(Screen):
    """Lists and manages bank accounts."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        root = box_layout(orientation="vertical", spacing=10, padding=12)
        self.status_label = status_label("No data loaded")
        self.items_label = body_label("")
        refresh_btn = button("Refresh banks")
        refresh_btn.bind(on_release=lambda *_: self.refresh())

        self.name_input = text_field("Bank name")
        self.account_type_input = text_field("Account type (corriente/ahorro)")
        self.currency_input = text_field("Currency (EUR)")
        self.delete_id_input = text_field("Bank ID to deactivate", numeric=True)

        create_btn = button("Create bank")
        create_btn.bind(on_release=lambda *_: self.create_bank())
        delete_btn = button("Deactivate bank", outlined=True)
        delete_btn.bind(on_release=lambda *_: self.delete_bank())

        content = box_layout(orientation="vertical", spacing=8, size_hint_y=None)
        content.bind(minimum_height=content.setter("height"))

        list_card = card_container()
        list_card.add_widget(title_label("Active banks"))
        list_card.add_widget(self.status_label)
        list_card.add_widget(self.items_label)
        list_card.add_widget(refresh_btn)

        create_card = card_container()
        create_card.add_widget(title_label("Create bank"))
        create_card.add_widget(self.name_input)
        create_card.add_widget(self.account_type_input)
        create_card.add_widget(self.currency_input)
        create_card.add_widget(create_btn)

        delete_card = card_container()
        delete_card.add_widget(title_label("Deactivate bank"))
        delete_card.add_widget(self.delete_id_input)
        delete_card.add_widget(delete_btn)

        content.add_widget(list_card)
        content.add_widget(create_card)
        content.add_widget(delete_card)

        scroll = ScrollView(size_hint=(1, 1))
        scroll.add_widget(content)
        root.add_widget(scroll)
        self.add_widget(root)

    def refresh(self) -> None:
        self.status_label.text = "Loading banks..."

        def work():
            app = App.get_running_app()
            return app.api_client.list_banks(active_only=True)

        def on_success(banks):
            if not banks:
                self.status_label.text = "No banks found"
                self.items_label.text = ""
                return
            lines = format_bank_lines(banks)
            self.items_label.text = "\n".join(lines)
            self.status_label.text = f"Loaded {len(banks)} banks"

        def on_error(exc: Exception):
            self.status_label.text = f"Error: {exc}"

        run_background(work, on_success, on_error)

    def create_bank(self) -> None:
        name = self.name_input.text.strip()
        account_type = self.account_type_input.text.strip() or "corriente"
        currency = self.currency_input.text.strip() or "EUR"
        if not name:
            self.status_label.text = "Bank name is required"
            return

        payload = {
            "nombre": name,
            "tipo_cuenta": account_type,
            "saldo_inicial": "0",
            "moneda": currency,
            "notas": None,
        }
        self.status_label.text = "Creating bank..."

        def work():
            app = App.get_running_app()
            return app.api_client.create_bank(payload)

        def on_success(_bank):
            self.status_label.text = "Bank created"
            self.name_input.text = ""
            self.refresh()

        def on_error(exc: Exception):
            if isinstance(exc, ApiClientError):
                self.status_label.text = f"Error: {exc}"
            else:
                self.status_label.text = f"Unexpected error: {exc}"

        run_background(work, on_success, on_error)

    def delete_bank(self) -> None:
        raw_id = self.delete_id_input.text.strip()
        if not raw_id:
            self.status_label.text = "Bank ID is required"
            return
        bank_id = int(raw_id)
        self.status_label.text = "Deactivating bank..."

        def work():
            app = App.get_running_app()
            return app.api_client.delete_bank(bank_id)

        def on_success(_result):
            self.status_label.text = "Bank deactivated"
            self.delete_id_input.text = ""
            self.refresh()

        def on_error(exc: Exception):
            self.status_label.text = f"Error: {exc}"

        run_background(work, on_success, on_error)
