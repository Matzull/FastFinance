"""Kivy app entrypoint for FastFinance mobile."""

from __future__ import annotations

from kivy.core.window import Window
from kivy.metrics import dp
from kivy.uix.screenmanager import ScreenManager
from kivy.uix.scrollview import ScrollView
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDButton, MDButtonIcon, MDButtonText, MDIconButton
from kivymd.uix.label import MDLabel

from patrimonio.mobile.api_client import FastFinanceApiClient
from patrimonio.mobile.config import SettingsStore
from patrimonio.mobile.screens import (
    BanksScreen,
    BudgetsScreen,
    DashboardScreen,
    InsightsScreen,
    NetWorthScreen,
    SettingsScreen,
    SubscriptionsScreen,
    TransactionsScreen,
)


class FastFinanceMobileApp(MDApp):
    """Root Kivy app for Android/Desktop mobile module."""

    def build(self):
        Window.clearcolor = (0.92, 0.95, 0.99, 1)

        self.settings_store = SettingsStore()
        self.settings = self.settings_store.load()
        self.api_client = FastFinanceApiClient(base_url=self.settings.base_url)

        self.theme_cls.theme_style = "Light"

        root = MDBoxLayout(orientation="vertical", spacing=0)

        header = MDBoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(64),
            padding=(dp(14), 0, dp(10), 0),
            spacing=dp(8),
            md_bg_color=(0.07, 0.25, 0.55, 1),
        )
        title_block = MDBoxLayout(orientation="vertical", spacing=0)
        title_block.add_widget(
            MDLabel(
                text="FastFinance",
                halign="left",
                valign="middle",
                theme_text_color="Custom",
                text_color=(1, 1, 1, 1),
            )
        )
        self.section_label = MDLabel(
            text="Dashboard",
            halign="left",
            valign="middle",
            theme_text_color="Custom",
            text_color=(0.82, 0.90, 0.98, 1),
            size_hint_y=None,
            height=dp(16),
        )
        title_block.add_widget(self.section_label)
        header.add_widget(title_block)

        refresh_btn = MDIconButton(icon="refresh")
        refresh_btn.theme_icon_color = "Custom"
        refresh_btn.icon_color = (1, 1, 1, 1)
        refresh_btn.bind(on_release=lambda *_: self.refresh_current())
        header.add_widget(refresh_btn)
        root.add_widget(header)

        self.screen_manager = ScreenManager()
        self.screen_manager.add_widget(DashboardScreen(name="dashboard"))
        self.screen_manager.add_widget(TransactionsScreen(name="transactions"))
        self.screen_manager.add_widget(BanksScreen(name="banks"))
        self.screen_manager.add_widget(SubscriptionsScreen(name="subscriptions"))
        self.screen_manager.add_widget(NetWorthScreen(name="net_worth"))
        self.screen_manager.add_widget(BudgetsScreen(name="budgets"))
        self.screen_manager.add_widget(InsightsScreen(name="insights"))
        self.screen_manager.add_widget(SettingsScreen(name="settings"))

        body = MDBoxLayout(orientation="vertical", padding=(dp(10), dp(10), dp(10), dp(8)))
        body.add_widget(self.screen_manager)
        root.add_widget(body)

        nav = MDBoxLayout(
            size_hint=(None, None),
            height=dp(76),
            spacing=dp(8),
            padding=(dp(12), dp(10), dp(12), dp(8)),
            md_bg_color=(0.95, 0.97, 1, 1),
        )
        nav.bind(minimum_width=nav.setter("width"))

        self.nav_items = {}

        for screen_name, title, icon in [
            ("dashboard", "Dashboard", "view-dashboard-outline"),
            ("transactions", "Tx", "swap-horizontal"),
            ("banks", "Banks", "bank-outline"),
            ("subscriptions", "Subs", "calendar-refresh"),
            ("net_worth", "Net", "chart-timeline-variant"),
            ("budgets", "Budgets", "wallet-outline"),
            ("insights", "Insights", "lightbulb-outline"),
            ("settings", "Settings", "cog-outline"),
        ]:
            nav_item = MDButton(
                MDButtonIcon(icon=icon),
                MDButtonText(text=title),
                style="text",
                size_hint=(None, None),
                theme_width="Custom",
                width=dp(126),
                height=dp(48),
            )
            nav_item.bind(on_release=lambda _, s=screen_name: self.switch_to(s))
            self.nav_items[screen_name] = nav_item
            nav.add_widget(nav_item)

        nav_scroll = ScrollView(
            do_scroll_x=True,
            do_scroll_y=False,
            size_hint=(1, None),
            height=dp(76),
            bar_width=dp(3),
        )
        nav_scroll.add_widget(nav)
        root.add_widget(nav_scroll)

        self._set_active_nav("dashboard")

        return root

    def switch_to(self, screen_name: str) -> None:
        self.screen_manager.current = screen_name
        self.section_label.text = screen_name.replace("_", " ").title()
        self._set_active_nav(screen_name)

    def _set_active_nav(self, screen_name: str) -> None:
        for name, widget in self.nav_items.items():
            widget.style = "filled" if name == screen_name else "text"
            if name == screen_name:
                widget.md_bg_color = (0.15, 0.40, 0.84, 1)

    def refresh_current(self) -> None:
        current = self.screen_manager.current_screen
        refresh = getattr(current, "refresh", None)
        if callable(refresh):
            refresh()


def main() -> None:
    """Entry point used by `fastfinance-mobile` script."""
    FastFinanceMobileApp().run()


if __name__ == "__main__":
    main()
