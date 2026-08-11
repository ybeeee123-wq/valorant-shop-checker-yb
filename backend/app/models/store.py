from pydantic import BaseModel


class SkinOffer(BaseModel):
    uuid: str
    name: str
    display_icon: str
    content_tier_uuid: str
    content_tier_name: str
    content_tier_color: str
    cost: int


class BundleItem(BaseModel):
    uuid: str
    name: str
    display_icon: str
    base_price: int
    discounted_price: int
    discount_percent: float


class Bundle(BaseModel):
    uuid: str
    name: str
    display_icon: str | None = None
    items: list[BundleItem]
    total_base_price: int
    total_discounted_price: int
    duration_remaining_secs: int


class Wallet(BaseModel):
    valorant_points: int
    radianite_points: int


class DailyStoreResponse(BaseModel):
    offers: list[SkinOffer]
    seconds_remaining: int


class BundleResponse(BaseModel):
    bundles: list[Bundle]


class NightMarketOffer(BaseModel):
    bonus_offer_id: str
    offer_id: str
    uuid: str
    name: str
    display_icon: str
    content_tier_uuid: str
    content_tier_name: str
    content_tier_color: str
    original_cost: int
    discounted_cost: int
    discount_percent: int
    is_seen: bool


class NightMarketResponse(BaseModel):
    active: bool
    offers: list[NightMarketOffer]
    seconds_remaining: int
