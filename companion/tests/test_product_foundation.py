import json
import urllib.request
from datetime import datetime, timedelta, timezone

import pytest

import preferences
from callback import LocalCallback
from credentials import CredentialStore
from local_riot import LocalRiotClient
from local_store import LocalStore


class MemoryCredentials:
    def __init__(self) -> None:
        self.values: dict[tuple[str, str], str] = {}

    def get_password(self, service: str, name: str) -> str | None:
        return self.values.get((service, name))

    def set_password(self, service: str, name: str, value: str) -> None:
        self.values[(service, name)] = value

    def delete_password(self, service: str, name: str) -> None:
        self.values.pop((service, name), None)


def test_credentials_and_riot_session_restore() -> None:
    backend = MemoryCredentials()
    credentials = CredentialStore(backend)
    session = {
        "access_token": "sensitive" * 500,
        "puuid": "player",
        "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
    }
    credentials.save_riot_session(session)
    credentials.save_device_token("device-secret")
    assert LocalRiotClient(credentials).session == session
    assert json.loads(backend.values[("VALSHOP", "riot_session")])["format"] == "chunked-v1"
    assert len([name for service, name in backend.values if name.startswith("riot_session.")]) > 1
    assert credentials.device_token() == "device-secret"
    credentials.clear_riot_session()
    credentials.clear_device_token()
    assert credentials.riot_session() is None
    assert credentials.device_token() == ""


def test_legacy_single_value_riot_session_is_still_readable() -> None:
    backend = MemoryCredentials()
    backend.set_password("VALSHOP", "riot_session", json.dumps({"puuid": "legacy"}))
    credentials = CredentialStore(backend)
    assert credentials.riot_session() == {"puuid": "legacy"}
    credentials.clear_riot_session()
    assert credentials.riot_session() is None


def test_offline_queue_history_and_notification_dedupe(tmp_path) -> None:
    store = LocalStore(str(tmp_path / "cache.db"))
    shop = {
        "rotation_key": "rotation-1",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "seconds_remaining": 300,
        "offers": [{"uuid": "skin", "name": "Skin", "cost": 875}],
    }
    store.save_shop(shop)
    assert store.get_cache("shop")["rotation_key"] == "rotation-1"
    assert store.pending() == [shop]
    assert len(store.history()) == 1
    assert store.should_notify("rotation-1", "skin") is True
    assert store.should_notify("rotation-1", "skin") is False
    store.mark_uploaded("rotation-1")
    assert store.pending() == []


def test_preferences_persist(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "settings.json"
    monkeypatch.setattr(preferences, "SETTINGS_FILE", path)
    first = preferences.Preferences()
    first.set("launch_minimized", True)
    assert preferences.Preferences().get("launch_minimized") is True


def test_callback_listener_lifecycle() -> None:
    callback = LocalCallback(port=0)
    callback.start()
    try:
        with urllib.request.urlopen(
            f"http://127.0.0.1:{callback.port}/redirect", timeout=2
        ) as response:
            assert response.status == 200
        payload = json.dumps(
            {"url": "http://localhost/redirect#access_token=test"}
        ).encode()
        request = urllib.request.Request(
            f"http://127.0.0.1:{callback.port}/complete",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=2) as response:
            assert response.status == 200
        assert callback.wait(timeout=2).endswith("access_token=test")
        assert callback.server is None
    finally:
        callback.stop()
