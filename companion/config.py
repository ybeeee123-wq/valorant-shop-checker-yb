import json
import sys
from pathlib import Path

from pydantic_settings import BaseSettings


def _release_values() -> dict:
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
    try:
        return json.loads((root / "release_config.json").read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


release = _release_values()


class Settings(BaseSettings):
    API_BASE_URL: str = release.get("api_base_url", "http://localhost:8000")
    PUBLIC_SITE_URL: str = release.get("public_site_url", "http://localhost:5173")
    UPDATE_METADATA_URL: str = release.get("update_metadata_url", "")
    UPDATE_DOWNLOAD_URL: str = release.get("update_download_url", "")
    COMPANION_DEVICE_NAME: str = "Windows PC"
    COMPANION_DEV_INTERVAL_SECONDS: int = 0
    COMPANION_JITTER_SECONDS: int = 90
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
