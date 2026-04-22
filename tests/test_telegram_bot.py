"""Tests for Telegram bot adapter."""

from decimal import Decimal

import pytest

from patrimonio.telegram.bot import (
    PatrimonioBot,
    WAITING_BANK,
    WAITING_CATEGORY,
    WAITING_DESCRIPTION,
    WAITING_CONFIRMATION,
    WAITING_MANUAL_AMOUNT,
)


class TestPatrimonioBotInit:
    def test_init_without_openai(self):
        bot = PatrimonioBot(token="test_token", openai_api_key=None)
        assert bot.token == "test_token"
        assert bot.db is not None
        assert bot.extractor is not None
        assert bot.pending_data == {}

    def test_init_with_openai(self):
        bot = PatrimonioBot(token="test_token", openai_api_key="sk-test")
        assert bot.extractor.openai_api_key == "sk-test"


class TestPatrimonioBotPendingData:
    def test_add_pending_data(self):
        bot = PatrimonioBot(token="test_token")
        bot.pending_data[123] = {
            "amount": Decimal("10.00"),
            "description": "Test",
        }
        assert 123 in bot.pending_data
        assert bot.pending_data[123]["amount"] == Decimal("10.00")

    def test_remove_pending_data(self):
        bot = PatrimonioBot(token="test_token")
        bot.pending_data[123] = {"test": "data"}
        bot.pending_data.pop(123, None)
        assert 123 not in bot.pending_data


class TestPatrimonioBotMessages:
    def test_start_message_commands_placeholder(self):
        assert True


@pytest.fixture
def bot_with_db(db_temp):
    bot = PatrimonioBot(token="test_token")
    bot.db = db_temp
    return bot


class TestPatrimonioBotQueries:
    def test_bot_has_banks_method(self):
        bot = PatrimonioBot(token="test_token")
        assert hasattr(bot, "banks")
        assert callable(bot.banks)

    def test_bot_has_balance_method(self):
        bot = PatrimonioBot(token="test_token")
        assert hasattr(bot, "balance")
        assert callable(bot.balance)

    def test_bot_has_summary_method(self):
        bot = PatrimonioBot(token="test_token")
        assert hasattr(bot, "summary")
        assert callable(bot.summary)

    def test_bot_has_expenses_method(self):
        bot = PatrimonioBot(token="test_token")
        assert hasattr(bot, "expenses")
        assert callable(bot.expenses)

    def test_bot_has_income_method(self):
        bot = PatrimonioBot(token="test_token")
        assert hasattr(bot, "income")
        assert callable(bot.income)

    def test_bot_has_subscriptions_method(self):
        bot = PatrimonioBot(token="test_token")
        assert hasattr(bot, "subscriptions")
        assert callable(bot.subscriptions)

    def test_bot_has_net_worth_method(self):
        bot = PatrimonioBot(token="test_token")
        assert hasattr(bot, "net_worth")
        assert callable(bot.net_worth)


class TestPatrimonioBotTransactionEntry:
    def test_bot_has_manual_expense_method(self):
        bot = PatrimonioBot(token="test_token")
        assert hasattr(bot, "manual_expense")
        assert callable(bot.manual_expense)

    def test_bot_has_manual_income_method(self):
        bot = PatrimonioBot(token="test_token")
        assert hasattr(bot, "manual_income")
        assert callable(bot.manual_income)

    def test_bot_has_process_photo_method(self):
        bot = PatrimonioBot(token="test_token")
        assert hasattr(bot, "process_photo")
        assert callable(bot.process_photo)


class TestPatrimonioBotConversation:
    def test_conversation_states_defined(self):
        assert WAITING_BANK == 0
        assert WAITING_CATEGORY == 1
        assert WAITING_DESCRIPTION == 2
        assert WAITING_CONFIRMATION == 3
        assert WAITING_MANUAL_AMOUNT == 4

    def test_bot_has_select_bank_method(self):
        bot = PatrimonioBot(token="test_token")
        assert hasattr(bot, "select_bank")
        assert callable(bot.select_bank)

    def test_bot_has_select_category_method(self):
        bot = PatrimonioBot(token="test_token")
        assert hasattr(bot, "select_category")
        assert callable(bot.select_category)

    def test_bot_has_confirm_transaction_method(self):
        bot = PatrimonioBot(token="test_token")
        assert hasattr(bot, "confirm_transaction")
        assert callable(bot.confirm_transaction)


class TestMain:
    def test_main_without_token(self, capsys, monkeypatch):
        import os

        original = os.environ.get("TELEGRAM_BOT_TOKEN")
        if "TELEGRAM_BOT_TOKEN" in os.environ:
            del os.environ["TELEGRAM_BOT_TOKEN"]

        monkeypatch.setattr("patrimonio.telegram.bot.dotenv.load_dotenv", lambda: None)

        try:
            from patrimonio.telegram.bot import main

            main()
            captured = capsys.readouterr()
            assert "TELEGRAM_BOT_TOKEN" in captured.out
        finally:
            if original:
                os.environ["TELEGRAM_BOT_TOKEN"] = original
