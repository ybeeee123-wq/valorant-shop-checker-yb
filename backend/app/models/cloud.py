from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl

from app.models.store import Bundle, NightMarketResponse, Wallet


class SkinCatalogItem(BaseModel):
    uuid: str
    name: str
    display_icon: str
    weapon: str
    content_tier_uuid: str
    content_tier_name: str
    content_tier_color: str


class WishlistCreate(BaseModel):
    skin_uuid: str = Field(min_length=1, max_length=64)


class WishlistItemResponse(BaseModel):
    skin_uuid: str
    skin_name: str
    display_icon: str
    content_tier_name: str
    content_tier_color: str
    added_at: datetime


class SnapshotOffer(BaseModel):
    skin_uuid: str = Field(min_length=1, max_length=64)
    skin_name: str = Field(min_length=1, max_length=160)
    display_icon: str = ""
    content_tier_uuid: str = ""
    content_tier_name: str = "Unknown"
    content_tier_color: str = ""
    vp_cost: int = Field(ge=1)


class ShopSyncRequest(BaseModel):
    rotation_key: str | None = Field(default=None, max_length=40)
    seconds_remaining: int = Field(ge=0)
    offers: list[SnapshotOffer] = Field(max_length=10)
    bundles: list[Bundle] = Field(default_factory=list, max_length=10)
    night_market: NightMarketResponse = Field(
        default_factory=lambda: NightMarketResponse(active=False, offers=[], seconds_remaining=0)
    )
    wallet: Wallet = Field(default_factory=lambda: Wallet(valorant_points=0, radianite_points=0))
    reauth_required: bool = False


class HistorySnapshot(BaseModel):
    rotation_key: str
    fetched_at: datetime
    seconds_remaining: int
    offers: list[SnapshotOffer]


class NotificationPreferencesUpdate(BaseModel):
    web_push_enabled: bool
    discord_enabled: bool
    discord_webhook_url: HttpUrl | None = None
    remove_discord_webhook: bool = False
    notify_only_wishlist_matches: bool = True


class NotificationPreferencesResponse(BaseModel):
    web_push_enabled: bool
    discord_enabled: bool
    discord_configured: bool
    notify_only_wishlist_matches: bool


class PushSubscriptionRequest(BaseModel):
    endpoint: HttpUrl
    p256dh: str = Field(min_length=1, max_length=512)
    auth: str = Field(min_length=1, max_length=512)


class PushSubscriptionDelete(BaseModel):
    endpoint: HttpUrl


class NotificationTestRequest(BaseModel):
    channel: str = Field(pattern="^(web_push|discord)$")


class CompanionHeartbeat(BaseModel):
    reauth_required: bool = False


class CompanionStatus(BaseModel):
    registered: bool
    online: bool
    device_name: str | None = None
    last_seen_at: datetime | None = None
    last_successful_sync_at: datetime | None = None
    reauth_required: bool = False


class PairingStartRequest(BaseModel):
    challenge: str = Field(min_length=43, max_length=128, pattern=r"^[A-Za-z0-9_-]+$")
    verifier_hash: str = Field(min_length=64, max_length=64, pattern=r"^[a-f0-9]{64}$")
    device_name: str = Field(min_length=1, max_length=120)


class PairingApproveRequest(BaseModel):
    challenge: str = Field(min_length=43, max_length=128, pattern=r"^[A-Za-z0-9_-]+$")


class PairingPollRequest(BaseModel):
    challenge: str = Field(min_length=43, max_length=128, pattern=r"^[A-Za-z0-9_-]+$")
    verifier: str = Field(min_length=43, max_length=128, pattern=r"^[A-Za-z0-9_-]+$")


class PairingStatusResponse(BaseModel):
    status: str
    device_name: str | None = None
    device_token: str | None = None
