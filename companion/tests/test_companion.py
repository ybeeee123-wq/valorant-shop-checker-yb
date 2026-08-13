from datetime import datetime, timezone

import pytest

import riot_client
from riot_client import ReauthenticationRequired
from riot_client import sync_payload
from scheduler import backoff_seconds, next_check_at


def test_schedule_calculation() -> None:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    scheduled = next_check_at(100, jitter_seconds=15, now=now)
    assert (scheduled - now).total_seconds() == 115


def test_retry_backoff_is_bounded() -> None:
    assert backoff_seconds(0) == 30
    assert backoff_seconds(3) == 240
    assert backoff_seconds(20) == 3600


def test_cloud_sync_payload() -> None:
    payload = sync_payload({
        "seconds_remaining": 90,
        "offers": [{"uuid": "skin", "name": "Skin", "cost": 875}],
        "bundles": [{"uuid": "bundle"}],
        "night_market": {"active": False, "offers": [], "seconds_remaining": 0},
        "wallet": {"valorant_points": 100, "radianite_points": 20},
    })
    assert payload["seconds_remaining"] == 90
    assert payload["offers"][0]["skin_uuid"] == "skin"
    assert payload["offers"][0]["vp_cost"] == 875
    assert payload["bundles"][0]["uuid"] == "bundle"
    assert payload["wallet"]["valorant_points"] == 100


@pytest.mark.asyncio
async def test_expired_auth_reports_reauthentication(monkeypatch: pytest.MonkeyPatch) -> None:
    class Response:
        status_code = 401

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {}

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def get(self, *_args, **_kwargs):
            return Response()

    monkeypatch.setattr(riot_client.httpx, "AsyncClient", lambda **_kwargs: Client())
    with pytest.raises(ReauthenticationRequired):
        await riot_client.fetch_daily_store("http://localhost:8000", "device-token")
