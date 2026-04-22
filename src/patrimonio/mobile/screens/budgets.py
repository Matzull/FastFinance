"""Budgets screen with CRUD actions."""

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


class BudgetsScreen(Screen):
    """Shows and manages budget entities."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        root = box_layout(orientation="vertical", spacing=10, padding=12)
        self.status_label = status_label("No data loaded")
        self.items_label = body_label("")

        self.name_input = text_field("Budget name")
        self.category_input = text_field("Category", text="otros")
        self.limit_input = text_field("Limit")
        self.period_input = text_field("Period (mensual/semanal/anual)", text="mensual")
        self.target_id_input = text_field("Budget ID for update/delete", numeric=True)

        create_btn = button("Create budget")
        create_btn.bind(on_release=lambda *_: self.create_budget())
        update_btn = button("Update budget")
        update_btn.bind(on_release=lambda *_: self.update_budget())
        delete_btn = button("Delete budget", outlined=True)
        delete_btn.bind(on_release=lambda *_: self.delete_budget())
        refresh_btn = button("Refresh budgets")
        refresh_btn.bind(on_release=lambda *_: self.refresh())

        content = box_layout(orientation="vertical", spacing=8, size_hint_y=None)
        content.bind(minimum_height=content.setter("height"))

        list_card = card_container()
        list_card.add_widget(title_label("Budget status"))
        list_card.add_widget(self.status_label)
        list_card.add_widget(self.items_label)
        list_card.add_widget(refresh_btn)

        create_card = card_container()
        create_card.add_widget(title_label("Create or update"))
        create_card.add_widget(self.name_input)
        create_card.add_widget(self.category_input)
        create_card.add_widget(self.limit_input)
        create_card.add_widget(self.period_input)
        create_card.add_widget(create_btn)

        manage_card = card_container()
        manage_card.add_widget(title_label("Manage by ID"))
        manage_card.add_widget(self.target_id_input)
        manage_card.add_widget(update_btn)
        manage_card.add_widget(delete_btn)

        content.add_widget(list_card)
        content.add_widget(create_card)
        content.add_widget(manage_card)

        scroll = ScrollView(size_hint=(1, 1))
        scroll.add_widget(content)
        root.add_widget(scroll)
        self.add_widget(root)

    def refresh(self) -> None:
        self.status_label.text = "Loading budgets..."

        def work():
            app = App.get_running_app()
            return app.api_client.get_budget_status()

        def on_success(statuses):
            if not statuses:
                self.status_label.text = "No budgets found"
                self.items_label.text = ""
                return
            lines = []
            for status in statuses:
                budget_id = status.get("id", "-")
                name = status.get("nombre", "-")
                spent = status.get("gastado", 0)
                limit = status.get("limite", 0)
                pct = status.get("porcentaje", 0)
                lines.append(f"#{budget_id} - {name}: {spent}/{limit} ({pct:.1f}%)")
            self.items_label.text = "\n".join(lines)
            self.status_label.text = f"Loaded {len(statuses)} budgets"

        def on_error(exc: Exception):
            self.status_label.text = f"Error: {exc}"

        run_background(work, on_success, on_error)

    def create_budget(self) -> None:
        if not self.name_input.text.strip():
            self.status_label.text = "Budget name is required"
            return
        if not self.limit_input.text.strip():
            self.status_label.text = "Limit is required"
            return
        payload = {
            "nombre": self.name_input.text.strip(),
            "categoria": self.category_input.text.strip() or "otros",
            "limite": self.limit_input.text.strip(),
            "periodo": self.period_input.text.strip().lower() or "mensual",
            "color": "#8B5CF6",
            "icono": "fa-wallet",
            "notas": None,
        }
        self.status_label.text = "Creating budget..."

        def work():
            app = App.get_running_app()
            return app.api_client.create_budget(payload)

        def on_success(_result):
            self.status_label.text = "Budget created"
            self.refresh()

        def on_error(exc: Exception):
            self.status_label.text = f"Error: {exc}"

        run_background(work, on_success, on_error)

    def update_budget(self) -> None:
        raw_id = self.target_id_input.text.strip()
        if not raw_id:
            self.status_label.text = "Budget ID is required"
            return
        budget_id = int(raw_id)

        payload = {}
        if self.name_input.text.strip():
            payload["nombre"] = self.name_input.text.strip()
        if self.limit_input.text.strip():
            payload["limite"] = self.limit_input.text.strip()
        if not payload:
            self.status_label.text = "Provide name or limit to update"
            return

        self.status_label.text = "Updating budget..."

        def work():
            app = App.get_running_app()
            return app.api_client.update_budget(budget_id, payload)

        def on_success(_result):
            self.status_label.text = "Budget updated"
            self.refresh()

        def on_error(exc: Exception):
            self.status_label.text = f"Error: {exc}"

        run_background(work, on_success, on_error)

    def delete_budget(self) -> None:
        raw_id = self.target_id_input.text.strip()
        if not raw_id:
            self.status_label.text = "Budget ID is required"
            return
        budget_id = int(raw_id)
        self.status_label.text = "Deleting budget..."

        def work():
            app = App.get_running_app()
            return app.api_client.delete_budget(budget_id)

        def on_success(_result):
            self.status_label.text = "Budget deleted"
            self.target_id_input.text = ""
            self.refresh()

        def on_error(exc: Exception):
            self.status_label.text = f"Error: {exc}"

        run_background(work, on_success, on_error)
