"""Helpers to execute backend calls without blocking the UI thread."""

from __future__ import annotations

import os
from collections.abc import Callable
from threading import Thread
from typing import TypeVar

T = TypeVar("T")


def _run_on_ui_thread(callback: Callable[..., None], *args) -> None:
    if os.environ.get("PYTEST_CURRENT_TEST"):
        callback(*args)
        return

    try:
        from kivy.clock import Clock

        Clock.schedule_once(lambda _dt: callback(*args), 0)
    except Exception:
        callback(*args)


def run_background(
    work: Callable[[], T],
    on_success: Callable[[T], None],
    on_error: Callable[[Exception], None],
) -> None:
    """Runs work in a background thread and marshals callbacks to UI thread."""

    def runner() -> None:
        try:
            result = work()
            _run_on_ui_thread(on_success, result)
        except Exception as exc:  # pragma: no cover - error path validated in tests
            _run_on_ui_thread(on_error, exc)

    Thread(target=runner, daemon=True).start()
