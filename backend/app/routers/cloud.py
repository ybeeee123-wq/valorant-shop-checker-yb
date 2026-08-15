import secrets
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.cloud import (
    CompanionHeartbeat,
    CompanionStatus,
    HistorySnapshot,
    NotificationPreferencesResponse,
    NotificationPreferencesUpdate,
    NotificationTestRequest,
    PairingApproveRequest,
    PairingPollRequest,
    PairingStartRequest,
    PairingStatusResponse,
    PushSubscriptionDelete,
    PushSubscriptionRequest,
    ShopSyncRequest,
    SkinCatalogItem,
    SkinPreviewResponse,
    SnapshotOffer,
    UserNotificationResponse,
    WishlistCreate,
    WishlistItemResponse,
)
from app.models.persistence import (
    CompanionDevice,
    CompanionPairingChallenge,
    PushSubscription,
    ShopSnapshot,
    User,
    UserNotification,
    WishlistItem,
)
from app.routers.auth import authenticated_user
from app.services import asset_cache, storefront
from app.services.cloud import (
    decrypt_secret,
    encrypt_secret,
    evaluate_latest_snapshot,
    get_notification_contact,
    get_preferences,
    notify_matches,
    record_snapshot,
    record_storefront_state,
    secure_hash,
    send_discord,
    send_email,
    send_web_push,
    token_hash,
    validate_discord_webhook,
    validate_email_address,
)
from app.session_store import store as session_store

router = APIRouter()
_pairing_lock = threading.Lock()
_pairing_requests: dict[str, list[float]] = {}


def _check_pairing_rate(ip: str) -> None:
    now = time.monotonic()
    with _pairing_lock:
        recent = [value for value in _pairing_requests.get(ip, []) if now - value < 60]
        if len(recent) >= 12:
            raise HTTPException(status_code=429, detail="Too many pairing requests")
        recent.append(now)
        _pairing_requests[ip] = recent


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def current_user(user: User = Depends(authenticated_user)) -> User:
    return user


def companion_device(
    authorization: str = Header(default=""), db: Session = Depends(get_db)
) -> CompanionDevice:
    token = authorization[7:] if authorization.startswith("Bearer ") else ""
    device = db.scalar(select(CompanionDevice).where(
        CompanionDevice.device_token_hash == token_hash(token), CompanionDevice.revoked.is_(False)
    )) if token else None
    if not device:
        raise HTTPException(status_code=401, detail="Invalid companion token")
    return device


@router.get("/skins", response_model=list[SkinCatalogItem])
def skins(
    q: str = Query(default="", max_length=80), weapon: str = Query(default="", max_length=40),
    limit: int = Query(default=100, ge=1, le=200), _: User = Depends(current_user),
) -> list[dict[str, Any]]:
    return asset_cache.search_skins(q, weapon, limit)


@router.get("/skins/{skin_uuid}/preview", response_model=SkinPreviewResponse)
def skin_preview(
    skin_uuid: str, _: User = Depends(current_user)
) -> dict[str, Any]:
    preview = asset_cache.get_skin_preview(skin_uuid)
    if not preview:
        raise HTTPException(status_code=404, detail="Skin preview not found")
    return preview


@router.get("/wishlist", response_model=list[WishlistItemResponse])
def wishlist(user: User = Depends(current_user), db: Session = Depends(get_db)) -> list[WishlistItem]:
    return list(db.scalars(select(WishlistItem).where(WishlistItem.user_id == user.id).order_by(WishlistItem.added_at.desc())).all())


@router.post("/wishlist", response_model=WishlistItemResponse, status_code=201)
async def add_wishlist(body: WishlistCreate, user: User = Depends(current_user), db: Session = Depends(get_db)) -> WishlistItem:
    existing = db.scalar(select(WishlistItem).where(WishlistItem.user_id == user.id, WishlistItem.skin_uuid == body.skin_uuid.lower()))
    if existing:
        return existing
    skin = asset_cache.get_skin(body.skin_uuid)
    if not skin:
        raise HTTPException(status_code=404, detail="Skin not found")
    tier = asset_cache.get_content_tier(skin.get("contentTierUuid", ""))
    item = WishlistItem(
        user_id=user.id, skin_uuid=skin["uuid"], skin_name=skin.get("displayName", "Unknown"),
        display_icon=skin.get("displayIcon", ""), content_tier_name=tier["name"] if tier else "Unknown",
        content_tier_color=tier["highlight_color"] if tier else "",
    )
    db.add(item); db.commit(); db.refresh(item)
    await evaluate_latest_snapshot(db, user.id)
    return item


@router.delete("/wishlist/{skin_uuid}", status_code=204)
def remove_wishlist(skin_uuid: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> None:
    db.execute(delete(WishlistItem).where(WishlistItem.user_id == user.id, WishlistItem.skin_uuid == skin_uuid.lower()))
    db.commit()


@router.get("/history", response_model=list[HistorySnapshot])
def history(user: User = Depends(current_user), db: Session = Depends(get_db)) -> list[HistorySnapshot]:
    snapshots = db.scalars(select(ShopSnapshot).where(ShopSnapshot.user_id == user.id).order_by(ShopSnapshot.fetched_at.desc()).limit(30)).all()
    return [HistorySnapshot(
        rotation_key=s.rotation_key, fetched_at=s.fetched_at, seconds_remaining=s.seconds_remaining,
        offers=[SnapshotOffer(
            skin_uuid=i.skin_uuid, skin_name=i.skin_name, display_icon=i.display_icon,
            content_tier_name=i.content_tier_name, content_tier_color=i.content_tier_color,
            vp_cost=i.vp_cost,
        ) for i in s.items],
    ) for s in snapshots]


@router.get("/notifications/preferences", response_model=NotificationPreferencesResponse)
def notification_preferences(user: User = Depends(current_user), db: Session = Depends(get_db)) -> NotificationPreferencesResponse:
    prefs = get_preferences(db, user.id)
    contact = get_notification_contact(db, user.id)
    return NotificationPreferencesResponse(
        web_push_enabled=prefs.web_push_enabled, discord_enabled=prefs.discord_enabled,
        discord_configured=bool(prefs.discord_webhook_encrypted),
        email_enabled=contact.email_enabled,
        email_configured=bool(contact.email_encrypted),
        notify_only_wishlist_matches=prefs.notify_only_wishlist_matches,
    )


@router.put("/notifications/preferences", response_model=NotificationPreferencesResponse)
def update_notification_preferences(body: NotificationPreferencesUpdate, user: User = Depends(current_user), db: Session = Depends(get_db)) -> NotificationPreferencesResponse:
    prefs = get_preferences(db, user.id)
    if body.discord_webhook_url:
        webhook = str(body.discord_webhook_url)
        validate_discord_webhook(webhook)
        prefs.discord_webhook_encrypted = encrypt_secret(webhook)
    if body.remove_discord_webhook:
        prefs.discord_webhook_encrypted = None
    if body.discord_enabled and not prefs.discord_webhook_encrypted:
        raise HTTPException(status_code=400, detail="Configure a Discord webhook before enabling Discord")
    contact = get_notification_contact(db, user.id)
    if body.email_address:
        contact.email_encrypted = encrypt_secret(validate_email_address(body.email_address))
    if body.remove_email:
        contact.email_encrypted = None
    if body.email_enabled and not contact.email_encrypted:
        raise HTTPException(status_code=400, detail="Configure an email address before enabling email")
    if body.email_enabled and not settings.RESEND_API_KEY:
        raise HTTPException(status_code=503, detail="Email delivery is not configured yet")
    prefs.web_push_enabled = body.web_push_enabled
    prefs.discord_enabled = body.discord_enabled
    contact.email_enabled = body.email_enabled
    prefs.notify_only_wishlist_matches = body.notify_only_wishlist_matches
    db.commit()
    return notification_preferences(user, db)


@router.get("/notifications/vapid-public-key")
def vapid_public_key(_: User = Depends(current_user)) -> dict[str, str]:
    return {"public_key": settings.VAPID_PUBLIC_KEY}


@router.post("/notifications/push/subscribe", status_code=204)
def subscribe_push(body: PushSubscriptionRequest, user: User = Depends(current_user), db: Session = Depends(get_db)) -> None:
    endpoint = str(body.endpoint)
    subscription = db.scalar(select(PushSubscription).where(PushSubscription.user_id == user.id, PushSubscription.endpoint == endpoint))
    if subscription:
        subscription.p256dh, subscription.auth = body.p256dh, body.auth
    else:
        db.add(PushSubscription(user_id=user.id, endpoint=endpoint, p256dh=body.p256dh, auth=body.auth))
    db.commit()


@router.delete("/notifications/push/subscribe", status_code=204)
def unsubscribe_push(body: PushSubscriptionDelete, user: User = Depends(current_user), db: Session = Depends(get_db)) -> None:
    db.execute(delete(PushSubscription).where(PushSubscription.user_id == user.id, PushSubscription.endpoint == str(body.endpoint)))
    db.commit()


@router.post("/notifications/test")
async def test_notification(body: NotificationTestRequest, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict[str, str]:
    try:
        if body.channel == "web_push":
            await send_web_push(db, user.id, "VALSHOP test", "Wishlist notifications are ready.")
        elif body.channel == "discord":
            prefs = get_preferences(db, user.id)
            if not prefs.discord_webhook_encrypted:
                raise ValueError("Discord webhook is not configured")
            await send_discord(decrypt_secret(prefs.discord_webhook_encrypted), "VALSHOP test — Discord notifications are ready.")
        else:
            contact = get_notification_contact(db, user.id)
            if not contact.email_encrypted:
                raise ValueError("Email address is not configured")
            await send_email(
                decrypt_secret(contact.email_encrypted), "VALSHOP test",
                "Email wishlist notifications are ready.", "", "/settings",
            )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"status": "sent"}


@router.get("/notifications", response_model=list[UserNotificationResponse])
def notifications(
    user: User = Depends(current_user), db: Session = Depends(get_db),
) -> list[UserNotification]:
    return list(db.scalars(
        select(UserNotification)
        .where(UserNotification.user_id == user.id)
        .order_by(UserNotification.created_at.desc())
        .limit(50)
    ).all())


@router.post("/notifications/{notification_id}/read", status_code=204)
def read_notification(
    notification_id: str, user: User = Depends(current_user), db: Session = Depends(get_db),
) -> None:
    notification = db.scalar(select(UserNotification).where(
        UserNotification.id == notification_id,
        UserNotification.user_id == user.id,
    ))
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    notification.read_at = datetime.now(timezone.utc)
    db.commit()


@router.post("/notifications/read-all", status_code=204)
def read_all_notifications(
    user: User = Depends(current_user), db: Session = Depends(get_db),
) -> None:
    items = db.scalars(select(UserNotification).where(
        UserNotification.user_id == user.id,
        UserNotification.read_at.is_(None),
    )).all()
    now = datetime.now(timezone.utc)
    for item in items:
        item.read_at = now
    db.commit()


@router.post("/companion/pairing/start", response_model=PairingStatusResponse)
def pairing_start(
    body: PairingStartRequest, request: Request, db: Session = Depends(get_db)
) -> PairingStatusResponse:
    _check_pairing_rate(request.client.host if request.client else "unknown")
    hashed = secure_hash(body.challenge)
    if db.scalar(select(CompanionPairingChallenge).where(CompanionPairingChallenge.challenge_hash == hashed)):
        raise HTTPException(status_code=409, detail="Pairing challenge already exists")
    pairing = CompanionPairingChallenge(
        challenge_hash=hashed,
        verifier_hash=body.verifier_hash,
        device_name=body.device_name,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
    )
    db.add(pairing); db.commit()
    return PairingStatusResponse(status="pending", device_name=body.device_name)


@router.get("/companion/pairing/status", response_model=PairingStatusResponse)
def pairing_status(
    challenge: str = Query(min_length=43, max_length=128),
    _: User = Depends(current_user), db: Session = Depends(get_db),
) -> PairingStatusResponse:
    pairing = db.scalar(select(CompanionPairingChallenge).where(
        CompanionPairingChallenge.challenge_hash == secure_hash(challenge)
    ))
    if not pairing or _aware(pairing.expires_at) <= datetime.now(timezone.utc) or pairing.used_at:
        return PairingStatusResponse(status="expired")
    return PairingStatusResponse(
        status="approved" if pairing.completed_at else "pending",
        device_name=pairing.device_name,
    )


@router.post("/companion/pairing/approve", response_model=PairingStatusResponse)
def pairing_approve(
    body: PairingApproveRequest, user: User = Depends(current_user), db: Session = Depends(get_db)
) -> PairingStatusResponse:
    pairing = db.scalar(select(CompanionPairingChallenge).where(
        CompanionPairingChallenge.challenge_hash == secure_hash(body.challenge)
    ))
    now = datetime.now(timezone.utc)
    if not pairing or _aware(pairing.expires_at) <= now or pairing.used_at:
        raise HTTPException(status_code=410, detail="Pairing challenge expired")
    if pairing.completed_at:
        raise HTTPException(status_code=409, detail="Pairing challenge already approved")
    raw_token = secrets.token_urlsafe(32)
    device = CompanionDevice(
        user_id=user.id, device_name=pairing.device_name,
        device_token_hash=token_hash(raw_token),
    )
    db.add(device)
    pairing.user_id = user.id
    pairing.device_token_encrypted = encrypt_secret(raw_token)
    pairing.completed_at = now
    db.commit()
    return PairingStatusResponse(status="approved", device_name=pairing.device_name)


@router.post("/companion/pairing/poll", response_model=PairingStatusResponse)
def pairing_poll(
    body: PairingPollRequest, request: Request, db: Session = Depends(get_db)
) -> PairingStatusResponse:
    _check_pairing_rate(request.client.host if request.client else "unknown")
    pairing = db.scalar(select(CompanionPairingChallenge).where(
        CompanionPairingChallenge.challenge_hash == secure_hash(body.challenge)
    ))
    now = datetime.now(timezone.utc)
    if not pairing or _aware(pairing.expires_at) <= now or pairing.used_at:
        return PairingStatusResponse(status="expired")
    pairing.poll_attempts += 1
    if pairing.poll_attempts > 60 or secure_hash(body.verifier) != pairing.verifier_hash:
        db.commit()
        raise HTTPException(status_code=401, detail="Invalid pairing verifier")
    if not pairing.completed_at or not pairing.device_token_encrypted:
        db.commit()
        return PairingStatusResponse(status="pending", device_name=pairing.device_name)
    token = decrypt_secret(pairing.device_token_encrypted)
    pairing.device_token_encrypted = None
    pairing.used_at = now
    db.commit()
    return PairingStatusResponse(
        status="approved", device_name=pairing.device_name, device_token=token
    )


@router.delete("/companion/device", status_code=204)
def revoke_companion(user: User = Depends(current_user), db: Session = Depends(get_db)) -> None:
    devices = db.scalars(select(CompanionDevice).where(CompanionDevice.user_id == user.id)).all()
    for device in devices:
        device.revoked = True
    db.commit()


@router.delete("/companion/self", status_code=204)
def revoke_current_companion(
    device: CompanionDevice = Depends(companion_device), db: Session = Depends(get_db)
) -> None:
    """Revoke only the credential used for this request.

    Keeping this separate from the browser-session management endpoint prevents a
    desktop disconnect on one PC from signing out the user's other PCs.
    """
    device.revoked = True
    db.commit()


@router.get("/companion/wishlist", response_model=list[WishlistItemResponse])
def companion_wishlist(
    device: CompanionDevice = Depends(companion_device), db: Session = Depends(get_db)
) -> list[WishlistItem]:
    return list(db.scalars(select(WishlistItem).where(
        WishlistItem.user_id == device.user_id
    ).order_by(WishlistItem.added_at.desc())).all())


@router.post("/companion/wishlist", response_model=WishlistItemResponse, status_code=201)
async def companion_add_wishlist(
    body: WishlistCreate, device: CompanionDevice = Depends(companion_device),
    db: Session = Depends(get_db),
) -> WishlistItem:
    user = db.get(User, device.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return await add_wishlist(body, user, db)


@router.delete("/companion/wishlist/{skin_uuid}", status_code=204)
def companion_remove_wishlist(
    skin_uuid: str, device: CompanionDevice = Depends(companion_device),
    db: Session = Depends(get_db),
) -> None:
    db.execute(delete(WishlistItem).where(
        WishlistItem.user_id == device.user_id,
        WishlistItem.skin_uuid == skin_uuid.lower(),
    ))
    db.commit()


@router.get("/companion/history", response_model=list[HistorySnapshot])
def companion_history(
    device: CompanionDevice = Depends(companion_device), db: Session = Depends(get_db)
) -> list[HistorySnapshot]:
    user = db.get(User, device.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return history(user, db)


@router.post("/companion/heartbeat")
def heartbeat(body: CompanionHeartbeat, device: CompanionDevice = Depends(companion_device), db: Session = Depends(get_db)) -> dict[str, str]:
    device.last_seen_at = datetime.now(timezone.utc); device.reauth_required = body.reauth_required; db.commit()
    return {"status": "ok"}


@router.get("/companion/shop")
async def companion_shop(
    device: CompanionDevice = Depends(companion_device), db: Session = Depends(get_db)
) -> dict[str, Any]:
    user = db.get(User, device.user_id)
    session = session_store.find_active_by_puuid(user.puuid) if user else None
    if not session:
        device.reauth_required = True; device.last_seen_at = datetime.now(timezone.utc); db.commit()
        raise HTTPException(status_code=401, detail="Riot reauthentication required")
    try:
        raw = await storefront.fetch_storefront(session.access_token, session.entitlements_token, session.puuid, session.shard)
        daily = storefront.get_daily_store(raw)
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Could not fetch Riot storefront") from exc
    return daily.model_dump()


@router.post("/companion/shop-sync")
async def companion_sync(body: ShopSyncRequest, device: CompanionDevice = Depends(companion_device), db: Session = Depends(get_db)) -> dict[str, int | bool | str]:
    device.last_seen_at = datetime.now(timezone.utc); device.reauth_required = body.reauth_required
    if body.reauth_required:
        db.commit(); return {"created": False, "notifications_sent": 0, "rotation_key": ""}
    snapshot, created = record_snapshot(db, device.user_id, body)
    record_storefront_state(db, device.user_id, body)
    sent = await notify_matches(db, device.user_id, snapshot)
    device.last_successful_sync_at = datetime.now(timezone.utc); device.reauth_required = False; db.commit()
    return {"created": created, "notifications_sent": sent, "rotation_key": snapshot.rotation_key}


@router.get("/companion/status", response_model=CompanionStatus)
def companion_status(user: User = Depends(current_user), db: Session = Depends(get_db)) -> CompanionStatus:
    device = db.scalar(select(CompanionDevice).where(CompanionDevice.user_id == user.id, CompanionDevice.revoked.is_(False)).order_by(CompanionDevice.created_at.desc()))
    if not device:
        return CompanionStatus(registered=False, online=False)
    last_seen = device.last_seen_at
    if last_seen and last_seen.tzinfo is None:
        last_seen = last_seen.replace(tzinfo=timezone.utc)
    online = bool(last_seen and last_seen >= datetime.now(timezone.utc) - timedelta(minutes=10))
    return CompanionStatus(
        registered=True, online=online, device_name=device.device_name,
        last_seen_at=device.last_seen_at, last_successful_sync_at=device.last_successful_sync_at,
        reauth_required=device.reauth_required,
    )
