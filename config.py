"""
Settings management with validation.
Loads settings.json (gitignored) and validates required fields.
"""

import json
import sys
from pathlib import Path
from typing import Literal

_SETTINGS_FILE = Path(__file__).parent / "settings.json"
_EXAMPLE_FILE = Path(__file__).parent / "settings.example.json"

_DEFAULTS = {
    "api_key": "",
    "provider": "",            # "" (auto-detect) | "gemini" | "groq" | "mistral"
    "poll_interval": 1.0,
    "response_mode": "auto",   # "auto" (popup) | "type" (direct typing)
    "model": "gemini-2.0-flash-lite",
    "type_speed": 0.015,
    "language": "he",
}

VALID_RESPONSE_MODES = ("auto", "type")
VALID_PROVIDERS = ("", "gemini", "groq", "mistral")


class ConfigError(Exception):
    """Raised when settings.json is missing or invalid."""
    pass


def _validate(settings: dict) -> dict:
    """Validate settings values, raising ConfigError on invalid configuration."""
    if settings["response_mode"] not in VALID_RESPONSE_MODES:
        raise ConfigError(
            f"response_mode must be one of {VALID_RESPONSE_MODES}, "
            f"got: {settings['response_mode']!r}"
        )

    if settings["provider"] not in VALID_PROVIDERS:
        raise ConfigError(
            f"provider must be one of {VALID_PROVIDERS}, "
            f"got: {settings['provider']!r}"
        )

    if settings["poll_interval"] <= 0:
        raise ConfigError("poll_interval must be greater than 0")

    if settings["type_speed"] < 0:
        raise ConfigError("type_speed must be non-negative")

    return settings


def is_api_key_configured(settings: dict) -> bool:
    """Check whether a real (non-placeholder) API key is present."""
    key = settings.get("api_key", "")
    return bool(key) and "YOUR_" not in key


def load() -> dict:
    """
    Load settings.json, merging with defaults and validating values.
    Creates settings.json from settings.example.json on first run.
    """
    if not _SETTINGS_FILE.exists():
        if _EXAMPLE_FILE.exists():
            import shutil
            shutil.copy(_EXAMPLE_FILE, _SETTINGS_FILE)
        else:
            _SETTINGS_FILE.write_text(
                json.dumps(_DEFAULTS, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        return _DEFAULTS.copy()

    with open(_SETTINGS_FILE, encoding="utf-8") as f:
        raw = json.load(f)

    merged = {**_DEFAULTS, **raw}
    return _validate(merged)


def reload() -> dict:
    """Reload settings from disk. Updates the module-level Settings dict in place."""
    global Settings
    Settings.clear()
    Settings.update(load())
    return Settings


Settings = load()
