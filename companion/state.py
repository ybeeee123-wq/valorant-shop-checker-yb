import json
from pathlib import Path

import keyring

SERVICE = "VALSHOP Companion"
STATE_DIR = Path.home() / ".valshop-companion"
STATE_FILE = STATE_DIR / "state.json"


def save_credentials(device_token: str, device_id: str = "") -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    keyring.set_password(SERVICE, "device_token", device_token)
    STATE_FILE.write_text(json.dumps({"device_id": device_id}), encoding="utf-8")


def credentials() -> str:
    return keyring.get_password(SERVICE, "device_token") or ""
