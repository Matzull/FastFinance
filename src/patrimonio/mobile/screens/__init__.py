"""Screen package for the FastFinance Kivy app."""

from patrimonio.mobile.screens.banks import BanksScreen
from patrimonio.mobile.screens.budgets import BudgetsScreen
from patrimonio.mobile.screens.dashboard import DashboardScreen
from patrimonio.mobile.screens.insights import InsightsScreen
from patrimonio.mobile.screens.net_worth import NetWorthScreen
from patrimonio.mobile.screens.settings import SettingsScreen
from patrimonio.mobile.screens.subscriptions import SubscriptionsScreen
from patrimonio.mobile.screens.transactions import TransactionsScreen

__all__ = [
    "DashboardScreen",
    "TransactionsScreen",
    "BanksScreen",
    "SubscriptionsScreen",
    "NetWorthScreen",
    "BudgetsScreen",
    "InsightsScreen",
    "SettingsScreen",
]
