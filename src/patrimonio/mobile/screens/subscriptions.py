"""Subscriptions screen with CRUD actions."""

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
    status_label,
    text_field,
    title_label,
)


class SubscriptionsScreen(Screen):
    """Lists and manages subscriptions."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        root = box_layout(orientation="vertical", spacing=10, padding=12)
        self.status_label = status_label("No data loaded")
        self.items_label = body_label("")

        self.bank_id_input = text_field("Bank ID", numeric=True)
        self.name_input = text_field("Subscription name")
        self.amount_input = text_field("Amount")
        self.frequency_input = text_field("Frequency (mensual/semanal/anual)", text="mensual")
        self.cancel_id_input = text_field("Subscription ID to cancel", numeric=True)

        create_btn = button("Create subscription")
        create_btn.bind(on_release=lambda *_: self.create_subscription())
        cancel_btn = button("Cancel subscription", outlined=True)
        cancel_btn.bind(on_release=lambda *_: self.cancel_subscription())
        refresh_btn = button("Refresh subscriptions")
        refresh_btn.bind(on_release=lambda *_: self.refresh())

        content = box_layout(orientation="vertical", spacing=8, size_hint_y=None)
        content.bind(minimum_height=content.setter("height"))

        list_card = card_container()
        list_card.add_widget(title_label("Active subscriptions"))
        list_card.add_widget(self.status_label)
        list_card.add_widget(self.items_label)
        list_card.add_widget(refresh_btn)

        create_card = card_container()
        create_card.add_widget(title_label("Create subscription"))
        create_card.add_widget(self.bank_id_input)
        create_card.add_widget(self.name_input)
        create_card.add_widget(self.amount_input)
        create_card.add_widget(self.frequency_input)
        create_card.add_widget(create_btn)

        cancel_card = card_container()
        cancel_card.add_widget(title_label("Cancel subscription"))
        cancel_card.add_widget(self.cancel_id_input)
        cancel_card.add_widget(cancel_btn)

        content.add_widget(list_card)
        content.add_widget(create_card)
        content.add_widget(cancel_card)

        scroll = ScrollView(size_hint=(1, 1))
        scroll.add_widget(content)
        root.add_widget(scroll)
        self.add_widget(root)

    def refresh(self) -> None:
        self.status_label.text = "Loading subscriptions..."

        def work():
            app = App.get_running_app()
            return app.api_client.list_subscriptions(active_only=True)

        def on_success(subs):
            if not subs:
                self.status_label.text = "No active subscriptions"
                self.items_label.text = ""
                return
            lines = []
            for sub in subs:
                sub_id = sub.get("id", "-")
                name = sub.get("nombre", "-")
                amount = sub.get("cantidad", "0")
                frequency = sub.get("frecuencia", "")
                lines.append(f"#{sub_id} - {name}: {amount}/{frequency}")
            self.items_label.text = "\n".join(lines)
            self.status_label.text = f"Loaded {len(subs)} subscriptions"

        def on_error(exc: Exception):
            self.status_label.text = f"Error: {exc}"

        run_background(work, on_success, on_error)

    def create_subscription(self) -> None:
        if not self.bank_id_input.text.strip():
            self.status_label.text = "Bank ID is required"
            return
        if not self.name_input.text.strip():
            self.status_label.text = "Name is required"
            return
        if not self.amount_input.text.strip():
            self.status_label.text = "Amount is required"
            return

        payload = {
            "banco_id": int(self.bank_id_input.text.strip()),
            "nombre": self.name_input.text.strip(),
            "cantidad": self.amount_input.text.strip(),
            "frecuencia": self.frequency_input.text.strip().lower() or "mensual",
            "fecha_inicio": None,
            "categoria": "suscripciones",
            "notas": None,
        }
        self.status_label.text = "Creating subscription..."

        def work():
            app = App.get_running_app()
            return app.api_client.create_subscription(payload)

        def on_success(_sub):
            self.status_label.text = "Subscription created"
            self.name_input.text = ""
            self.amount_input.text = ""
            self.refresh()

        def on_error(exc: Exception):
            self.status_label.text = f"Error: {exc}"

        run_background(work, on_success, on_error)

    def cancel_subscription(self) -> None:
        raw_id = self.cancel_id_input.text.strip()
        if not raw_id:
            self.status_label.text = "Subscription ID is required"
            return
        subscription_id = int(raw_id)
        self.status_label.text = "Cancelling subscription..."

        def work():
            app = App.get_running_app()
            return app.api_client.cancel_subscription(subscription_id)

        def on_success(_result):
            self.status_label.text = "Subscription canceled"
            self.cancel_id_input.text = ""
            self.refresh()

        def on_error(exc: Exception):
            self.status_label.text = f"Error: {exc}"

        run_background(work, on_success, on_error)
