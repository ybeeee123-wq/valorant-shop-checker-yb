import logging
from typing import Any, cast

import httpx

from app.models.store import (
    Bundle,
    BundleItem,
    BundleResponse,
    DailyStoreResponse,
    NightMarketOffer,
    NightMarketResponse,
    SkinOffer,
    Wallet,
)
from app.services.asset_cache import (
    CLIENT_PLATFORM,
    get_bundle_info,
    get_client_version,
    get_content_tier,
    get_skin,
)

logger = logging.getLogger(__name__)

VP_CURRENCY_ID = "85ad13f7-3d1b-5128-9eb2-7cd8ee0b5741"
RADIANITE_CURRENCY_ID = "e59aa87c-4cbf-517a-5983-6e81511be9b7"


def _riot_headers(access_token: str, entitlements_token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {access_token}",
        "X-Riot-Entitlements-JWT": entitlements_token,
        "X-Riot-ClientPlatform": CLIENT_PLATFORM,
        "X-Riot-ClientVersion": get_client_version(),
        "Content-Type": "application/json",
    }


async def fetch_storefront(
    access_token: str, entitlements_token: str, puuid: str, shard: str
) -> dict[str, Any]:
    """Fetch raw storefront JSON from Riot's API."""
    url = f"https://pd.{shard}.a.pvp.net/store/v3/storefront/{puuid}"
    logger.info("Fetching storefront: %s (version=%s)", url, get_client_version())
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            url, headers=_riot_headers(access_token, entitlements_token), json={},
        )
        if not resp.is_success:
            logger.error(
                "Storefront request failed: %s %s — body: %s",
                resp.status_code, resp.reason_phrase, resp.text[:500],
            )
            resp.raise_for_status()
        return cast(dict[str, Any], resp.json())


def _resolve_skin_offer(offer: dict[str, Any]) -> SkinOffer | None:
    """Resolve a single store offer dict into a SkinOffer model."""
    offer_id = offer.get("OfferID", "")
    cost = offer.get("Cost", {}).get(VP_CURRENCY_ID, 0)

    # The offer ID itself may be a skin level UUID
    item_uuid = offer_id
    # Also check Rewards for the actual item ID
    rewards = offer.get("Rewards", [])
    if rewards:
        item_uuid = rewards[0].get("ItemID", offer_id)

    skin = get_skin(item_uuid) or get_skin(offer_id)
    if not skin:
        logger.warning("Unknown skin UUID: %s (offer %s)", item_uuid, offer_id)
        return SkinOffer(
            uuid=offer_id,
            name="Unknown Skin",
            display_icon="",
            content_tier_uuid="",
            content_tier_name="Unknown",
            content_tier_color="",
            cost=cost,
        )

    tier_uuid = skin.get("contentTierUuid", "")
    tier = get_content_tier(tier_uuid)
    tier_name = tier["name"] if tier else "Unknown"
    tier_color = tier["highlight_color"] if tier else ""

    return SkinOffer(
        uuid=skin["uuid"],
        name=skin.get("displayName", "Unknown"),
        display_icon=skin.get("displayIcon", "") or "",
        content_tier_uuid=tier_uuid,
        content_tier_name=tier_name,
        content_tier_color=tier_color,
        cost=cost,
    )


def get_daily_store(raw_storefront: dict[str, Any]) -> DailyStoreResponse:
    """Parse the daily store from raw storefront data."""
    panel = raw_storefront.get("SkinsPanelLayout", {})
    raw_offers = panel.get("SingleItemStoreOffers", [])
    seconds_remaining = panel.get("SingleItemOffersRemainingDurationInSeconds", 0)

    offers: list[SkinOffer] = []
    for raw_offer in raw_offers:
        skin_offer = _resolve_skin_offer(raw_offer)
        if skin_offer:
            offers.append(skin_offer)

    return DailyStoreResponse(offers=offers, seconds_remaining=seconds_remaining)


def get_featured_bundle(raw_storefront: dict[str, Any]) -> BundleResponse:
    """Parse featured bundles from raw storefront data."""
    featured = raw_storefront.get("FeaturedBundle", {})
    raw_bundles = featured.get("Bundles", [])

    bundles: list[Bundle] = []
    for raw_bundle in raw_bundles:
        bundle_uuid = raw_bundle.get("DataAssetID", "")
        bundle_info = get_bundle_info(bundle_uuid)
        bundle_name = bundle_info["displayName"] if bundle_info else "Unknown Bundle"
        bundle_icon = (bundle_info.get("displayIcon", "") if bundle_info else "") or None

        duration = raw_bundle.get("DurationRemainingInSeconds", 0)

        items: list[BundleItem] = []
        total_base = 0
        total_discounted = 0

        for raw_item in raw_bundle.get("Items", []):
            item_uuid = raw_item.get("Item", {}).get("ItemID", "")
            base_price = raw_item.get("BasePrice", 0)
            discounted_price = raw_item.get("DiscountedPrice", base_price)
            discount_pct = raw_item.get("DiscountPercent", 0.0)

            skin = get_skin(item_uuid)
            item_name = skin["displayName"] if skin else "Unknown"
            item_icon = (skin.get("displayIcon", "") if skin else "") or ""

            items.append(BundleItem(
                uuid=item_uuid,
                name=item_name,
                display_icon=item_icon,
                base_price=base_price,
                discounted_price=discounted_price,
                discount_percent=discount_pct,
            ))

            total_base += base_price
            total_discounted += discounted_price

        bundles.append(Bundle(
            uuid=bundle_uuid,
            name=bundle_name,
            display_icon=bundle_icon,
            items=items,
            total_base_price=total_base,
            total_discounted_price=total_discounted,
            duration_remaining_secs=duration,
        ))

    return BundleResponse(bundles=bundles)


def get_night_market(raw_storefront: dict[str, Any]) -> NightMarketResponse:
    """Parse Night Market offers from the storefront's BonusStore payload."""
    bonus_store = raw_storefront.get("BonusStore")
    if not isinstance(bonus_store, dict):
        return NightMarketResponse(active=False, offers=[], seconds_remaining=0)

    raw_duration = bonus_store.get("BonusStoreRemainingDurationInSeconds", 0)
    if isinstance(raw_duration, (int, float)) and not isinstance(raw_duration, bool):
        seconds_remaining = max(0, int(raw_duration))
    else:
        logger.warning("Malformed Night Market duration: %r", raw_duration)
        seconds_remaining = 0

    raw_offers = bonus_store.get("BonusStoreOffers", [])
    if not isinstance(raw_offers, list):
        logger.warning("Malformed Night Market offers collection: %r", type(raw_offers).__name__)
        raw_offers = []

    offers: list[NightMarketOffer] = []
    for raw_bonus_offer in raw_offers:
        if not isinstance(raw_bonus_offer, dict):
            logger.warning("Skipping malformed Night Market offer: %r", raw_bonus_offer)
            continue

        bonus_offer_id = raw_bonus_offer.get("BonusOfferID")
        raw_offer = raw_bonus_offer.get("Offer")
        if not isinstance(bonus_offer_id, str) or not bonus_offer_id or not isinstance(raw_offer, dict):
            logger.warning("Skipping malformed Night Market offer header: %r", raw_bonus_offer)
            continue

        offer_id = raw_offer.get("OfferID")
        if not isinstance(offer_id, str) or not offer_id:
            logger.warning("Skipping Night Market offer %s with no OfferID", bonus_offer_id)
            continue

        discount_costs = raw_bonus_offer.get("DiscountCosts")
        discounted_cost = (
            discount_costs.get(VP_CURRENCY_ID) if isinstance(discount_costs, dict) else None
        )
        if (
            not isinstance(discounted_cost, (int, float))
            or isinstance(discounted_cost, bool)
            or discounted_cost <= 0
        ):
            logger.warning(
                "Skipping Night Market offer %s with invalid discounted VP price: %r",
                bonus_offer_id,
                discounted_cost,
            )
            continue

        costs = raw_offer.get("Cost")
        original_cost = costs.get(VP_CURRENCY_ID) if isinstance(costs, dict) else None
        if (
            not isinstance(original_cost, (int, float))
            or isinstance(original_cost, bool)
            or original_cost <= 0
        ):
            logger.warning(
                "Skipping Night Market offer %s with invalid original VP price: %r",
                bonus_offer_id,
                original_cost,
            )
            continue

        raw_discount_percent = raw_bonus_offer.get("DiscountPercent")
        if (
            not isinstance(raw_discount_percent, (int, float))
            or isinstance(raw_discount_percent, bool)
        ):
            logger.warning(
                "Skipping Night Market offer %s with invalid discount percentage: %r",
                bonus_offer_id,
                raw_discount_percent,
            )
            continue

        item_uuid = offer_id
        rewards = raw_offer.get("Rewards")
        if isinstance(rewards, list) and rewards and isinstance(rewards[0], dict):
            reward_item_id = rewards[0].get("ItemID")
            if isinstance(reward_item_id, str) and reward_item_id:
                item_uuid = reward_item_id

        skin = get_skin(item_uuid) or get_skin(offer_id)
        if skin:
            skin_uuid = skin["uuid"]
            skin_name = skin.get("displayName", "Unknown")
            display_icon = skin.get("displayIcon", "") or ""
            tier_uuid = skin.get("contentTierUuid", "")
            tier = get_content_tier(tier_uuid)
            tier_name = tier["name"] if tier else "Unknown"
            tier_color = tier["highlight_color"] if tier else ""
        else:
            logger.warning(
                "Unknown Night Market skin UUID: %s (offer %s)", item_uuid, offer_id
            )
            skin_uuid = item_uuid
            skin_name = "Unknown Skin"
            display_icon = ""
            tier_uuid = ""
            tier_name = "Unknown"
            tier_color = ""

        offers.append(NightMarketOffer(
            bonus_offer_id=bonus_offer_id,
            offer_id=offer_id,
            uuid=skin_uuid,
            name=skin_name,
            display_icon=display_icon,
            content_tier_uuid=tier_uuid,
            content_tier_name=tier_name,
            content_tier_color=tier_color,
            original_cost=int(original_cost),
            discounted_cost=int(discounted_cost),
            discount_percent=int(raw_discount_percent),
            is_seen=bool(raw_bonus_offer.get("IsSeen", False)),
        ))

    active = bool(offers) or seconds_remaining > 0
    if not active:
        return NightMarketResponse(active=False, offers=[], seconds_remaining=0)

    return NightMarketResponse(
        active=True,
        offers=offers,
        seconds_remaining=seconds_remaining,
    )


async def get_wallet(
    access_token: str, entitlements_token: str, puuid: str, shard: str
) -> Wallet:
    """Fetch VP and Radianite balance."""
    url = f"https://pd.{shard}.a.pvp.net/store/v1/wallet/{puuid}"
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url, headers=_riot_headers(access_token, entitlements_token))
        if not resp.is_success:
            logger.error(
                "Wallet request failed: %s %s — body: %s",
                resp.status_code, resp.reason_phrase, resp.text[:500],
            )
            resp.raise_for_status()
        data = resp.json()

    balances = data.get("Balances", {})
    return Wallet(
        valorant_points=balances.get(VP_CURRENCY_ID, 0),
        radianite_points=balances.get(RADIANITE_CURRENCY_ID, 0),
    )
