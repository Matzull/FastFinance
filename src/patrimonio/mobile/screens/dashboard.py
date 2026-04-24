"""Dashboard screen for the mobile app with visual KPI cards."""

from __future__ import annotations

from decimal import Decimal

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
    progress_bar,
    status_label,
    title_label,
)


class DashboardScreen(Screen):
    """Shows overall summary values from `/api/resumen` with KPI cards."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        root = box_layout(orientation="vertical", spacing=10, padding=12)

        self.status_label = status_label("Tap refresh to load summary")
        self.net_worth_kpi = kpi_card("Net Worth", "-", 0.07, 0.25, 0.55)
        self.balance_kpi = kpi_card("Month Balance", "-", 0.22, 0.70, 0.40)
        self.category_lines_label = body_label("No category data yet")
        self.income_label = status_label("Income: -")
        self.expenses_label = status_label("Expenses: -")

        self.income_bar = progress_bar(100, 0)
        self.expenses_bar = progress_bar(100, 0)

        details = box_layout(orientation="vertical", spacing=8, size_hint_y=None)
        details.bind(minimum_height=details.setter("height"))

        kpi_row = box_layout(orientation="horizontal", spacing=8, size_hint_y=None, height=dp(130))
        kpi_row.add_widget(self.net_worth_kpi)
        kpi_row.add_widget(self.balance_kpi)
        details.add_widget(kpi_row)

        summary_card = card_container()
        summary_card.add_widget(title_label("Monthly flow"))
        summary_card.add_widget(self.income_label)
        summary_card.add_widget(self.income_bar)
        summary_card.add_widget(self.expenses_label)
        summary_card.add_widget(self.expenses_bar)
        details.add_widget(summary_card)

        category_card = card_container()
        category_card.add_widget(title_label("Top expense categories"))
        category_card.add_widget(self.category_lines_label)
        details.add_widget(category_card)

        actions_card = card_container()
        actions_card.add_widget(title_label("Actions"))
        refresh_btn = button("Refresh")
        refresh_btn.bind(on_release=lambda *_: self.refresh())
        actions_card.add_widget(refresh_btn)
        details.add_widget(actions_card)

        scroll = ScrollView(size_hint=(1, 1))
        scroll.add_widget(details)

        root.add_widget(self.status_label)
        root.add_widget(scroll)
        self.add_widget(root)

    def on_pre_enter(self, *args):
        del args
        self.refresh()

    def refresh(self) -> None:
        self.status_label.text = "Loading summary..."

        def work():
            app = App.get_running_app()
            summary = app.api_client.get_summary()
            try:
                categories = app.api_client.expenses_by_category()
            except Exception:
                categories = []
            return summary, categories

        def on_success(result):
            summary, categories = result
            net_worth = Decimal(str(summary.get("patrimonio_neto", "0")))
            month = summary.get("resumen_mes_actual", {})
            balance = Decimal(str(month.get("balance", "0")))
            income = Decimal(str(month.get("ingresos", "0")))
            expenses = Decimal(str(month.get("gastos", "0")))

            self.net_worth_kpi.children[0].text = f"€{net_worth:,.0f}"
            self.balance_kpi.children[0].text = f"€{balance:,.0f}"
            self.income_label.text = f"Income: {income:,.2f} EUR"
            self.expenses_label.text = f"Expenses: {expenses:,.2f} EUR"

            self._render_month_bars(income, expenses, balance)
            self._render_categories(categories)
            self.status_label.text = "Summary loaded"

        def on_error(exc: Exception):
            self.status_label.text = f"Error: {exc}"

        run_background(work, on_success, on_error)

    def _render_month_bars(
        self,
        income: Decimal,
        expenses: Decimal,
        balance: Decimal,
    ) -> None:
        max_abs = max(abs(income), abs(expenses), abs(balance), Decimal("1"))
        self.income_bar.max = float(max_abs)
        self.expenses_bar.max = float(max_abs)
        self.income_bar.value = float(abs(income))
        self.expenses_bar.value = float(abs(expenses))

    def _render_categories(self, categories: list[dict]) -> None:
        if not categories:
            self.category_lines_label.text = "No category data available"
            return

        lines: list[str] = []
        for row in categories[:5]:
            name = row.get("categoria", "-")
            total = row.get("total", 0)
            lines.append(f"- {name}: {total}")
        self.category_lines_label.text = "\n".join(lines)
