import asyncio
import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

import httpx
from cryptography.fernet import Fernet, InvalidToken
from pywebpush import WebPushException, webpush  # type: ignore[import-untyped]
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.models.cloud import ShopSyncRequest, SnapshotOffer
from app.models.persistence import (
    NotificationEvent,
    NotificationPreference,
    PushSubscription,
    ShopSnapshot,
    ShopSnapshotItem,
    User,
    WishlistItem,
)
from app.models.store import SkinOffer

logger = logging.getLogger(__name__)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def secure_hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def get_or_create_user(db: Session, puuid: str) -> User:
    user = db.scalar(select(User).where(User.puuid == puuid))
    if user:
        return user
    user = User(puuid=puuid)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_preferences(db: Session, user_id: str) -> NotificationPreference:
    prefs = db.get(NotificationPreference, user_id)
    if not prefs:
        prefs = NotificationPreference(user_id=user_id)
        db.add(prefs)
        db.commit()
        db.refresh(prefs)
    return prefs


def rotation_key(seconds_remaining: int, now: datetime | None = None) -> str:
    current = now or datetime.now(timezone.utc)
    reset = current + timedelta(seconds=max(0, seconds_remaining))
    return reset.strftime("%Y%m%dT%H%MZ")


def record_snapshot(db: Session, user_id: str, sync: ShopSyncRequest) -> tuple[ShopSnapshot, bool]:
    key = sync.rotation_key or rotation_key(sync.seconds_remaining)
    existing = db.scalar(select(ShopSnapshot).where(
        ShopSnapshot.user_id == user_id, ShopSnapshot.rotation_key == key
    ))
    if existing:
        return existing, False
    snapshot = ShopSnapshot(
        user_id=user_id, rotation_key=key, seconds_remaining=sync.seconds_remaining,
        raw_offer_count=len(sync.offers),
    )
    snapshot.items = [ShopSnapshotItem(
        skin_uuid=item.skin_uuid.lower(), skin_name=item.skin_name,
        display_icon=item.display_icon, content_tier_name=item.content_tier_name,
        content_tier_color=item.content_tier_color, vp_cost=item.vp_cost,
    ) for item in sync.offers]
    db.add(snapshot)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(select(ShopSnapshot).where(
            ShopSnapshot.user_id == user_id, ShopSnapshot.rotation_key == key
        ))
        if existing:
            return existing, False
        raise
    db.refresh(snapshot)
    return snapshot, True


def validate_discord_webhook(url: str) -> None:
    parsed = urlparse(url)
    valid_host = parsed.hostname in {"discord.com", "discordapp.com"}
    if parsed.scheme != "https" or not valid_host or not parsed.path.startswith("/api/webhooks/"):
        raise ValueError("Enter a valid Discord webhook URL")


def _fernet() -> Fernet:
    if not settings.ENCRYPTION_KEY:
        raise RuntimeError("ENCRYPTION_KEY is required for Discord webhooks")
    return Fernet(settings.ENCRYPTION_KEY.encode())


def encrypt_secret(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def decrypt_secret(value: str) -> str:
    try:
        return _fernet().decrypt(value.encode()).decode()
    except InvalidToken as exc:
        raise RuntimeError("Stored Discord webhook cannot be decrypted") from exc


async def send_web_push(db: Session, user_id: str, title: str, body: str) -> int:
    if not settings.VAPID_PRIVATE_KEY or not settings.VAPID_PUBLIC_KEY:
        raise RuntimeError("VAPID keys are not configured")
    subscriptions = db.scalars(select(PushSubscription).where(PushSubscription.user_id == user_id)).all()
    payload = json.dumps({"title": title, "body": body, "url": settings.PUBLIC_SITE_URL})
    sent = 0
    for subscription in subscriptions:
        try:
            await asyncio.to_thread(
                webpush,
                subscription_info={"endpoint": subscription.endpoint, "keys": {"p256dh": subscription.p256dh, "auth": subscription.auth}},
                data=payload,
                vapid_private_key=settings.VAPID_PRIVATE_KEY,
                vapid_claims={"sub": settings.VAPID_SUBJECT},
            )
            subscription.last_used_at = datetime.now(timezone.utc)
            sent += 1
        except WebPushException as exc:
            logger.warning("Web Push delivery failed for subscription %s: %s", subscription.id, exc)
    db.commit()
    if not sent:
        raise RuntimeError("No Web Push subscription accepted the notification")
    return sent


async def send_discord(webhook: str, body: str) -> None:
    validate_discord_webhook(webhook)
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(webhook, json={"content": body})
        response.raise_for_status()


async def notify_matches(db: Session, user_id: str, snapshot: ShopSnapshot) -> int:
    wanted = {item.skin_uuid for item in db.scalars(select(WishlistItem).where(WishlistItem.user_id == user_id)).all()}
    prefs = get_preferences(db, user_id)
    matches = [item for item in snapshot.items if item.skin_uuid in wanted]
    sent = 0
    for item in matches:
        body = f"{item.skin_name} is in your shop today — {item.vp_cost:,} VP"
        channels = []
        if prefs.web_push_enabled:
            channels.append("web_push")
        if prefs.discord_enabled and prefs.discord_webhook_encrypted:
            channels.append("discord")
        for channel in channels:
            event = NotificationEvent(
                user_id=user_id, skin_uuid=item.skin_uuid,
                rotation_key=snapshot.rotation_key, channel=channel,
            )
            db.add(event)
            try:
                db.commit()
            except IntegrityError:
                db.rollback()
                continue
            try:
                if channel == "web_push":
                    await send_web_push(db, user_id, "VALSHOP wishlist match", body)
                else:
                    encrypted = prefs.discord_webhook_encrypted
                    if not encrypted:
                        continue
                    await send_discord(decrypt_secret(encrypted), body)
                event.status = "sent"
                event.sent_at = datetime.now(timezone.utc)
                sent += 1
            except Exception as exc:
                logger.warning("%s notification failed: %s", channel, exc)
                event.status = "failed"
                event.error = str(exc)[:500]
            db.commit()
    return sent


async def evaluate_latest_snapshot(db: Session, user_id: str) -> int:
    snapshot = db.scalar(
        select(ShopSnapshot)
        .where(ShopSnapshot.user_id == user_id)
        .order_by(ShopSnapshot.fetched_at.desc())
        .limit(1)
    )
    return await notify_matches(db, user_id, snapshot) if snapshot else 0


def sync_from_daily(offers: list[SkinOffer], seconds_remaining: int) -> ShopSyncRequest:
    return ShopSyncRequest(seconds_remaining=seconds_remaining, offers=[SnapshotOffer(
        skin_uuid=offer.uuid, skin_name=offer.name, display_icon=offer.display_icon,
        content_tier_name=offer.content_tier_name,
        content_tier_color=offer.content_tier_color, vp_cost=offer.cost,
    ) for offer in offers])
