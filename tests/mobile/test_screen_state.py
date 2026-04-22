"""Tests for mobile screen state helpers."""

from patrimonio.mobile.screen_state import (
    MobileRequestState,
    format_bank_lines,
    format_transaction_lines,
)


def test_mobile_request_state_transitions():
    state = MobileRequestState()
    assert state.loading is False

    state.set_loading("Loading...")
    assert state.loading is True
    assert state.message == "Loading..."

    state.set_success("Done")
    assert state.loading is False
    assert state.message == "Done"

    state.set_error("Failed")
    assert state.loading is False
    assert state.message == "Failed"


def test_format_bank_lines():
    banks = [
        {"id": 1, "nombre": "Main", "saldo_actual": "120.50"},
        {"id": 2, "nombre": "Savings", "saldo_actual": "300.00"},
    ]
    lines = format_bank_lines(banks)
    assert lines[0] == "#1 - Main: 120.50"
    assert lines[1] == "#2 - Savings: 300.00"


def test_format_transaction_lines_limit():
    txns = [
        {"id": 5, "cantidad": "10", "descripcion": "Coffee", "categoria": "comida"},
        {"id": 6, "cantidad": "20", "descripcion": "Taxi", "categoria": "transporte"},
    ]
    lines = format_transaction_lines(txns, limit=1)
    assert len(lines) == 1
    assert lines[0] == "#5 - 10 | Coffee (comida)"
