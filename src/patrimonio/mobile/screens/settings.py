"""Settings screen for mobile app configuration."""

from __future__ import annotations

from kivy.app import App
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView

from patrimonio.mobile.async_requests import run_background
from patrimonio.mobile.md_compat import (
    box_layout,
    button,
    card_container,
    notify,
    status_label,
    text_field,
    title_label,
)


class SettingsScreen(Screen):
    """Lets users configure the API base URL."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        root = box_layout(orientation="vertical", spacing=10, padding=12)

        self.status_label = status_label("")
        self.url_input = text_field("Backend base URL")

        save_btn = button("Save API URL")
        save_btn.bind(on_release=lambda *_: self.save())

        content = box_layout(orientation="vertical", spacing=8, size_hint_y=None)
        content.bind(minimum_height=content.setter("height"))
        card = card_container()
        card.add_widget(title_label("Backend configuration"))
        card.add_widget(self.url_input)
        card.add_widget(save_btn)
        card.add_widget(self.status_label)

        content.add_widget(card)

        scroll = ScrollView(size_hint=(1, 1))
        scroll.add_widget(content)
        root.add_widget(scroll)
        self.add_widget(root)

    def on_pre_enter(self, *args):
        del args
        app = App.get_running_app()
        self.url_input.text = app.settings.base_url

    def save(self) -> None:
        app = App.get_running_app()
        base_url = self.url_input.text.strip().rstrip("/")
        if not base_url:
            self.status_label.text = "Base URL cannot be empty"
            notify("Base URL cannot be empty")
            return

        app.settings.base_url = base_url
        app.settings_store.save(app.settings)
        app.api_client.set_base_url(base_url)
        self.status_label.text = "Saved. Verifying backend..."

        def work():
            return app.api_client.get_summary()

        def on_success(_summary):
            self.status_label.text = "Saved and backend is reachable"
            notify("Backend connected")

        def on_error(exc: Exception):
            self.status_label.text = f"Saved but backend check failed: {exc}"
            notify(f"Backend check failed: {exc}")

        run_background(work, on_success, on_error)
