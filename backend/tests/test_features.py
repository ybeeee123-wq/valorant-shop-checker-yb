import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from cryptography.fernet import Fernet
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from starlette.requests import Request

from app.config import settings
from app.database import Base
from app.models.cloud import (
    CompanionHeartbeat,
    NotificationPreferencesUpdate,
    PairingApproveRequest,
    PairingPollRequest,
    PairingStartRequest,
    ShopSyncRequest,
    SnapshotOffer,
    WishlistCreate,
)
from app.models.persistence import (
    CompanionDevice,
    CompanionPairingChallenge,
    NotificationContact,
    NotificationEvent,
    NotificationPreference,
    StorefrontState,
    User,
    UserNotification,
    WebSession,
    WishlistItem,
)
from app.routers.cloud import (
    add_wishlist,
    companion_device,
    heartbeat,
    notification_preferences,
    notifications,
    pairing_approve,
    pairing_poll,
    pairing_start,
    read_all_notifications,
    read_notification,
    remove_wishlist,
    revoke_companion,
    revoke_current_companion,
    update_notification_preferences,
)
from app.routers.store import daily_store, featured_bundle, night_market, wallet
from app.services import asset_cache
from app.services.cloud import (
    create_web_session,
    notify_matches,
    record_snapshot,
    record_storefront_state,
    resolve_web_session,
    revoke_web_session,
    token_hash,
)
from app.services.storefront import get_night_market


@pytest.fixture()
def db() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture()
def user(db: Session) -> User:
    value = User(puuid="player")
    db.add(value); db.commit(); db.refresh(value)
    return value


def test_wishlist_crud(db: Session, user: User, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(asset_cache, "get_skin", lambda _: {"uuid": "skin", "displayName": "Kuronami Vandal", "displayIcon": "icon", "contentTierUuid": "tier"})
    monkeypatch.setattr(asset_cache, "get_content_tier", lambda _: {"name": "Exclusive", "highlight_color": "fff"})
    item = asyncio.run(add_wishlist(WishlistCreate(skin_uuid="skin"), user, db))
    assert item.skin_name == "Kuronami Vandal"
    assert db.scalar(select(WishlistItem).where(WishlistItem.user_id == user.id))
    remove_wishlist("skin", user, db)
    assert db.scalar(select(WishlistItem).where(WishlistItem.user_id == user.id)) is None


def test_duplicate_rotation_is_deduplicated(db: Session, user: User) -> None:
    sync = ShopSyncRequest(rotation_key="rotation", seconds_remaining=10, offers=[SnapshotOffer(skin_uuid="skin", skin_name="Skin", vp_cost=875)])
    first, created = record_snapshot(db, user.id, sync)
    second, duplicate_created = record_snapshot(db, user.id, sync)
    assert created is True and duplicate_created is False and first.id == second.id


def test_full_storefront_state_and_durable_web_session(db: Session, user: User) -> None:
    sync = ShopSyncRequest(
        rotation_key="rotation",
        seconds_remaining=90,
        offers=[SnapshotOffer(
            skin_uuid="skin", skin_name="Skin", content_tier_uuid="tier", vp_cost=875
        )],
        bundles=[{
            "uuid": "bundle", "name": "Bundle", "items": [],
            "total_base_price": 1000, "total_discounted_price": 900,
            "duration_remaining_secs": 3600,
        }],
        night_market={
            "active": False, "offers": [], "seconds_remaining": 0,
        },
        wallet={"valorant_points": 100, "radianite_points": 20},
    )
    state = record_storefront_state(db, user.id, sync)
    assert db.get(StorefrontState, user.id) is state
    assert '"valorant_points": 100' in state.wallet_json
    assert '"content_tier_uuid": "tier"' in state.offers_json

    request = Request({
        "type": "http", "method": "GET", "path": "/", "headers": [],
        "client": ("127.0.0.1", 1234), "query_string": b"",
        "server": ("test", 80), "scheme": "http",
    })
    assert asyncio.run(daily_store(request, user, db)).offers[0].uuid == "skin"
    assert asyncio.run(featured_bundle(request, user, db)).bundles[0].uuid == "bundle"
    assert asyncio.run(wallet(request, user, db)).valorant_points == 100
    assert asyncio.run(night_market(request, user, db)).active is False

    created = create_web_session(db, user.id, "web-token")
    assert isinstance(created, WebSession)
    assert resolve_web_session(db, "web-token") is not None
    revoke_web_session(db, "web-token")
    assert resolve_web_session(db, "web-token") is None


def test_inactive_shop_is_safe() -> None:
    assert get_night_market({}).model_dump() == {"active": False, "offers": [], "seconds_remaining": 0}


def test_skin_preview_filters_missing_videos(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(asset_cache, "get_skin", lambda _: {
        "uuid": "skin",
        "displayName": "Kuronami Vandal",
        "displayIcon": "icon",
        "levels": [
            {"uuid": "level-one", "displayName": "Level 1", "streamedVideo": "https://riot.example/video.mp4"},
            {"uuid": "level-two", "displayName": "Level 2", "streamedVideo": None},
        ],
        "chromas": [
            {"uuid": "red", "displayName": "Red", "streamedVideo": "https://riot.example/red.mp4", "swatch": "red.png"},
        ],
    })
    preview = asset_cache.get_skin_preview("LEVEL-ONE")
    assert preview is not None
    assert [item["uuid"] for item in preview["levels"]] == ["level-one"]
    assert preview["chromas"][0]["swatch"] == "red.png"


def test_companion_auth_and_reauth_state(db: Session, user: User) -> None:
    device = CompanionDevice(user_id=user.id, device_name="PC", device_token_hash=token_hash("secret"))
    db.add(device); db.commit()
    assert companion_device("Bearer secret", db).id == device.id
    with pytest.raises(HTTPException):
        companion_device("Bearer wrong", db)
    heartbeat(CompanionHeartbeat(reauth_required=True), device, db)
    assert device.reauth_required is True and device.last_seen_at is not None


def test_match_and_duplicate_notification_prevention(db: Session, user: User, monkeypatch: pytest.MonkeyPatch) -> None:
    db.add(WishlistItem(user_id=user.id, skin_uuid="skin", skin_name="Skin"))
    db.add(NotificationPreference(user_id=user.id, web_push_enabled=True))
    db.commit()
    snapshot, _ = record_snapshot(db, user.id, ShopSyncRequest(rotation_key="rotation", seconds_remaining=10, offers=[SnapshotOffer(skin_uuid="skin", skin_name="Skin", vp_cost=875)]))

    async def sent(*_args, **_kwargs): return 1
    monkeypatch.setattr("app.services.cloud.send_web_push", sent)
    assert asyncio.run(notify_matches(db, user.id, snapshot)) == 1
    assert asyncio.run(notify_matches(db, user.id, snapshot)) == 0
    assert len(db.scalars(select(NotificationEvent)).all()) == 1
    inbox = db.scalars(select(UserNotification)).all()
    assert len(inbox) == 1 and inbox[0].skin_uuid == "skin" and inbox[0].vp_cost == 875


def test_existing_snapshot_new_wishlist_match_and_next_rotation(
    db: Session, user: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(asset_cache, "get_skin", lambda _: {"uuid": "skin", "displayName": "Kuronami Vandal", "displayIcon": "icon", "contentTierUuid": "tier"})
    monkeypatch.setattr(asset_cache, "get_content_tier", lambda _: {"name": "Exclusive", "highlight_color": "fff"})
    async def sent(*_args, **_kwargs): return 1
    monkeypatch.setattr("app.services.cloud.send_web_push", sent)
    db.add(NotificationPreference(user_id=user.id, web_push_enabled=True)); db.commit()
    record_snapshot(db, user.id, ShopSyncRequest(rotation_key="today", seconds_remaining=10, offers=[SnapshotOffer(skin_uuid="skin", skin_name="Kuronami Vandal", vp_cost=2375)]))
    asyncio.run(add_wishlist(WishlistCreate(skin_uuid="skin"), user, db))
    assert len(db.scalars(select(NotificationEvent)).all()) == 1
    today = db.scalar(select(NotificationEvent)); assert today and today.rotation_key == "today"
    next_snapshot, _ = record_snapshot(db, user.id, ShopSyncRequest(rotation_key="tomorrow", seconds_remaining=10, offers=[SnapshotOffer(skin_uuid="skin", skin_name="Kuronami Vandal", vp_cost=2375)]))
    assert asyncio.run(notify_matches(db, user.id, next_snapshot)) == 1
    assert len(db.scalars(select(NotificationEvent)).all()) == 2


def test_nonmatching_wishlist_does_not_notify(db: Session, user: User) -> None:
    db.add(WishlistItem(user_id=user.id, skin_uuid="other", skin_name="Other")); db.commit()
    snapshot, _ = record_snapshot(db, user.id, ShopSyncRequest(rotation_key="today", seconds_remaining=10, offers=[SnapshotOffer(skin_uuid="skin", skin_name="Skin", vp_cost=875)]))
    assert asyncio.run(notify_matches(db, user.id, snapshot)) == 0


def test_notification_inbox_is_scoped_and_markable(db: Session, user: User) -> None:
    other = User(puuid="other-player")
    db.add(other); db.commit(); db.refresh(other)
    own = UserNotification(
        user_id=user.id, skin_uuid="skin", rotation_key="today", title="Match",
        body="Skin is available", vp_cost=875,
    )
    foreign = UserNotification(
        user_id=other.id, skin_uuid="other", rotation_key="today", title="Other",
        body="Other is available", vp_cost=875,
    )
    db.add_all([own, foreign]); db.commit(); db.refresh(own); db.refresh(foreign)
    assert [item.id for item in notifications(user, db)] == [own.id]
    with pytest.raises(HTTPException) as denied:
        read_notification(foreign.id, user, db)
    assert denied.value.status_code == 404
    read_notification(own.id, user, db)
    assert own.read_at is not None
    own.read_at = None; db.commit()
    read_all_notifications(user, db)
    assert own.read_at is not None and foreign.read_at is None


def test_email_notification_preferences_are_encrypted(
    db: Session, user: User, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "ENCRYPTION_KEY", Fernet.generate_key().decode())
    monkeypatch.setattr(settings, "RESEND_API_KEY", "test-key")
    updated = update_notification_preferences(NotificationPreferencesUpdate(
        web_push_enabled=False, discord_enabled=False,
        email_enabled=True, email_address="Player@Example.com",
    ), user, db)
    assert updated.email_enabled and updated.email_configured
    contact = db.get(NotificationContact, user.id)
    assert contact and contact.email_encrypted and "player@example.com" not in contact.email_encrypted
    assert notification_preferences(user, db).email_configured


def _request() -> Request:
    return Request({"type": "http", "method": "POST", "path": "/", "headers": [], "client": ("127.0.0.1", 1234), "query_string": b"", "server": ("test", 80), "scheme": "http"})


def test_pairing_single_use_invalid_and_device_revocation(
    db: Session, user: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "ENCRYPTION_KEY", Fernet.generate_key().decode())
    challenge = "a" * 43; verifier = "b" * 43
    pairing_start(PairingStartRequest(challenge=challenge, verifier_hash=token_hash(verifier), device_name="Gaming PC"), _request(), db)
    with pytest.raises(HTTPException):
        pairing_poll(PairingPollRequest(challenge=challenge, verifier="c" * 43), _request(), db)
    pairing_approve(PairingApproveRequest(challenge=challenge), user, db)
    completed = pairing_poll(PairingPollRequest(challenge=challenge, verifier=verifier), _request(), db)
    assert completed.status == "approved" and completed.device_token
    assert pairing_poll(PairingPollRequest(challenge=challenge, verifier=verifier), _request(), db).status == "expired"
    revoke_companion(user, db)
    with pytest.raises(HTTPException):
        companion_device(f"Bearer {completed.device_token}", db)


def test_pairing_expiry_and_per_device_revocation(
    db: Session, user: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "ENCRYPTION_KEY", Fernet.generate_key().decode())
    challenge = "d" * 43
    verifier = "e" * 43
    pairing_start(
        PairingStartRequest(
            challenge=challenge,
            verifier_hash=token_hash(verifier),
            device_name="Old PC",
        ),
        _request(),
        db,
    )
    pairing = db.scalar(select(CompanionPairingChallenge))
    assert pairing
    pairing.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db.commit()
    assert pairing_poll(
        PairingPollRequest(challenge=challenge, verifier=verifier), _request(), db
    ).status == "expired"

    first = CompanionDevice(
        user_id=user.id, device_name="First", device_token_hash=token_hash("first")
    )
    second = CompanionDevice(
        user_id=user.id, device_name="Second", device_token_hash=token_hash("second")
    )
    db.add_all([first, second])
    db.commit()
    revoke_current_companion(first, db)
    with pytest.raises(HTTPException):
        companion_device("Bearer first", db)
    assert companion_device("Bearer second", db).id == second.id
