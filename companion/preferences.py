import json

from paths import SETTINGS_FILE, ensure_directories

DEFAULTS = {
    "onboarding_complete": False,
    "start_with_windows": False,
    "launch_minimized": False,
    "notifications_enabled": True,
    "close_notice_shown": False,
    "theme": "dark",
}


class Preferences:
    def __init__(self) -> None:
        ensure_directories()
        try:
            self.values = {**DEFAULTS, **json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))}
        except (FileNotFoundError, json.JSONDecodeError):
            self.values = dict(DEFAULTS)

    def get(self, key: str):
        return self.values.get(key)

    def set(self, key: str, value) -> None:
        self.values[key] = value
        SETTINGS_FILE.write_text(json.dumps(self.values, indent=2), encoding="utf-8")
