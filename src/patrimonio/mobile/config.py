"""Persistent settings for the mobile app."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path


DEFAULT_BASE_URL = "http://127.0.0.1:8000"


@dataclass
class MobileSettings:
    """Mutable app settings persisted to disk."""

    base_url: str = DEFAULT_BASE_URL


class SettingsStore:
    """Loads and saves mobile settings in a JSON file."""

    def __init__(self, settings_path: Path | None = None):
        if settings_path is None:
            settings_path = self._default_settings_path()
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        self.settings_path = settings_path

    @staticmethod
    def _default_settings_path() -> Path:
        """Resolve a writable settings path for desktop and Android."""
        android_private = os.environ.get("ANDROID_PRIVATE")
        if android_private:
            return Path(android_private) / ".fastfinance" / "mobile_settings.json"
        return Path.home() / ".fastfinance" / "mobile_settings.json"

    def load(self) -> MobileSettings:
        if not self.settings_path.exists():
            return MobileSettings()
        try:
            payload = json.loads(self.settings_path.read_text(encoding="utf-8"))
            base_url = str(payload.get("base_url", DEFAULT_BASE_URL)).strip()
            return MobileSettings(base_url=base_url or DEFAULT_BASE_URL)
        except Exception:
            return MobileSettings()

    def save(self, settings: MobileSettings) -> None:
        payload = {"base_url": settings.base_url.strip() or DEFAULT_BASE_URL}
        self.settings_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
