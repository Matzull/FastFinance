"""Tests for non-blocking request helper."""

import time

from patrimonio.mobile.async_requests import run_background


def test_run_background_success_callback():
    seen = {"value": None}

    def work():
        return 42

    def on_success(value):
        seen["value"] = value

    def on_error(_exc):
        seen["value"] = "error"

    run_background(work, on_success, on_error)
    for _ in range(20):
        if seen["value"] is not None:
            break
        time.sleep(0.01)

    assert seen["value"] == 42


def test_run_background_error_callback():
    seen = {"value": None}

    def work():
        raise ValueError("boom")

    def on_success(_value):
        seen["value"] = "ok"

    def on_error(exc):
        seen["value"] = str(exc)

    run_background(work, on_success, on_error)
    for _ in range(20):
        if seen["value"] is not None:
            break
        time.sleep(0.01)

    assert "boom" in seen["value"]
