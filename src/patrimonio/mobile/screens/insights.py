"""Insights screen with visual metric badges."""

from __future__ import annotations

from kivy.app import App
from kivy.metrics import dp
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView

from patrimonio.mobile.async_requests import run_background
from patrimonio.mobile.md_compat import (
    body_label,
    box_layout,
    button,
    card_container,
    kpi_card,
    notify,
    progress_bar,
    status_label,
    title_label,
)


class InsightsScreen(Screen):
    """Shows high-level insights with visual metrics."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        root = box_layout(orientation="vertical", spacing=10, padding=12)
        self.status_label = status_label("No data loaded")
        self.savings_kpi = kpi_card("Savings Rate", "-", 0.95, 0.56, 0.06)
        self.alerts_kpi = kpi_card("Active Alerts", "-", 0.91, 0.40, 0.14)
        self.items_label = body_label("")
        self.savings_bar = progress_bar(100, 0)
        self.alerts_bar = progress_bar(10, 0)
        refresh_btn = button("Refresh insights")
        refresh_btn.bind(on_release=lambda *_: self.refresh())

        content = box_layout(orientation="vertical", spacing=8, size_hint_y=None)
        content.bind(minimum_height=content.setter("height"))

        kpi_row = box_layout(orientation="horizontal", spacing=8, size_hint_y=None, height=dp(130))
        kpi_row.add_widget(self.savings_kpi)
        kpi_row.add_widget(self.alerts_kpi)
        content.add_widget(kpi_row)

        card = card_container()
        card.add_widget(title_label("Smart insights"))
        card.add_widget(self.status_label)
        card.add_widget(body_label("Savings progress"))
        card.add_widget(self.savings_bar)
        card.add_widget(body_label("Alert level"))
        card.add_widget(self.alerts_bar)
        card.add_widget(self.items_label)
        card.add_widget(refresh_btn)
        content.add_widget(card)

        scroll = ScrollView(size_hint=(1, 1))
        scroll.add_widget(content)
        root.add_widget(scroll)
        self.add_widget(root)

    def refresh(self) -> None:
        self.status_label.text = "Loading insights..."

        def work():
            app = App.get_running_app()
            return app.api_client.get_insights()

        def on_success(insights):
            savings = insights.get("tasa_ahorro", 0)
            category = insights.get("categoria_mayor_gasto", {})
            category_name = category.get("nombre") or "-"
            category_total = category.get("total", 0)
            alerts = insights.get("alertas", [])

            self.savings_bar.value = max(0, min(100, float(savings)))
            self.alerts_bar.value = max(0, min(10, float(len(alerts))))
            self.savings_kpi.children[0].text = f"{savings:.1f}%"
            self.alerts_kpi.children[0].text = f"{len(alerts)}"
            self.items_label.text = (
                f"Top expense category: {category_name} ({category_total})\n"
                f"Alerts currently raised: {len(alerts)}"
            )
            self.status_label.text = "Insights loaded"
            notify("Insights updated")

        def on_error(exc: Exception):
            self.status_label.text = f"Error: {exc}"
            notify(f"Insights error: {exc}")

        run_background(work, on_success, on_error)
