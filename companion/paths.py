from pathlib import Path

from platformdirs import user_data_dir, user_log_dir

APP_DIR = Path(user_data_dir("VALSHOP", appauthor=False))
LOG_DIR = Path(user_log_dir("VALSHOP", appauthor=False))
CACHE_DB = APP_DIR / "cache.db"
SETTINGS_FILE = APP_DIR / "settings.json"


def ensure_directories() -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
