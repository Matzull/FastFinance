"""Net worth screen with CRUD actions."""

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


class NetWorthScreen(Screen):
    """Shows and manages assets and liabilities."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        root = box_layout(orientation="vertical", spacing=10, padding=12)
        self.status_label = status_label("No data loaded")
        self.items_label = body_label("")

        self.name_input = text_field("Item name")
        self.type_input = text_field("Type: activo or pasivo", text="activo")
        self.value_input = text_field("Value")
        self.description_input = text_field("Description")
        self.delete_id_input = text_field("Item ID to delete", numeric=True)

        create_btn = button("Create net worth item")
        create_btn.bind(on_release=lambda *_: self.create_item())
        delete_btn = button("Delete net worth item", outlined=True)
        delete_btn.bind(on_release=lambda *_: self.delete_item())
        refresh_btn = button("Refresh net worth items")
        refresh_btn.bind(on_release=lambda *_: self.refresh())

        content = box_layout(orientation="vertical", spacing=8, size_hint_y=None)
        content.bind(minimum_height=content.setter("height"))

        list_card = card_container()
        list_card.add_widget(title_label("Assets and liabilities"))
        list_card.add_widget(self.status_label)
        list_card.add_widget(self.items_label)
        list_card.add_widget(refresh_btn)

        create_card = card_container()
        create_card.add_widget(title_label("Create item"))
        create_card.add_widget(self.name_input)
        create_card.add_widget(self.type_input)
        create_card.add_widget(self.value_input)
        create_card.add_widget(self.description_input)
        create_card.add_widget(create_btn)

        delete_card = card_container()
        delete_card.add_widget(title_label("Delete item"))
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
        self.status_label.text = "Loading net worth items..."

        def work():
            app = App.get_running_app()
            return app.api_client.list_net_worth_items()

        def on_success(items):
            if not items:
                self.status_label.text = "No net worth items"
                self.items_label.text = ""
                return
            lines = []
            for item in items:
                item_id = item.get("id", "-")
                name = item.get("nombre", "-")
                item_type = item.get("tipo", "-")
                value = item.get("valor", "0")
                lines.append(f"#{item_id} - {name} ({item_type}): {value}")
            self.items_label.text = "\n".join(lines)
            self.status_label.text = f"Loaded {len(items)} items"

        def on_error(exc: Exception):
            self.status_label.text = f"Error: {exc}"

        run_background(work, on_success, on_error)

    def create_item(self) -> None:
        if not self.name_input.text.strip():
            self.status_label.text = "Name is required"
            return
        if not self.value_input.text.strip():
            self.status_label.text = "Value is required"
            return

        payload = {
            "nombre": self.name_input.text.strip(),
            "tipo": self.type_input.text.strip().lower() or "activo",
            "valor": self.value_input.text.strip(),
            "descripcion": self.description_input.text.strip() or None,
            "fecha_adquisicion": None,
        }
        self.status_label.text = "Creating net worth item..."

        def work():
            app = App.get_running_app()
            return app.api_client.create_net_worth_item(payload)

        def on_success(_result):
            self.status_label.text = "Net worth item created"
            self.name_input.text = ""
            self.value_input.text = ""
            self.description_input.text = ""
            self.refresh()

        def on_error(exc: Exception):
            self.status_label.text = f"Error: {exc}"

        run_background(work, on_success, on_error)

    def delete_item(self) -> None:
        raw_id = self.delete_id_input.text.strip()
        if not raw_id:
            self.status_label.text = "Item ID is required"
            return
        item_id = int(raw_id)
        self.status_label.text = "Deleting net worth item..."

        def work():
            app = App.get_running_app()
            return app.api_client.delete_net_worth_item(item_id)

        def on_success(_result):
            self.status_label.text = "Net worth item deleted"
            self.delete_id_input.text = ""
            self.refresh()

        def on_error(exc: Exception):
            self.status_label.text = f"Error: {exc}"

        run_background(work, on_success, on_error)
