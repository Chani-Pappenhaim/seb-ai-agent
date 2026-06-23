import json
from pathlib import Path

_SETTINGS_FILE = Path(__file__).parent / "settings.json"

_DEFAULTS = {
    "api_key": "",
    "poll_interval": 1.0,
    "response_mode": "auto",   # "auto" | "popup" | "type"
    "model": "claude-haiku-4-5-20251001",
    "type_speed": 0.015,
    "language": "he",
}

def load() -> dict:
    if _SETTINGS_FILE.exists():
        with open(_SETTINGS_FILE, encoding="utf-8") as f:
            return {**_DEFAULTS, **json.load(f)}
    return _DEFAULTS.copy()

Settings = load()
