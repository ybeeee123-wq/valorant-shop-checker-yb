import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

BASE_URL = "https://valorant-api.com/v1"

CLIENT_PLATFORM = (
    "ew0KCSJwbGF0Zm9ybVR5cGUiOiAiUEMiLA0KCSJwbGF0Zm9ybU9TIjogIldpbmRvd3MiLA0KCSJwbGF0"
    "Zm9ybU9TVmVyc2lvbiI6ICIxMC4wLjE5MDQyLjEuMjU2LjY0Yml0IiwNCgkicGxhdGZvcm1DaGlwc2V0"
    "IjogIlVua25vd24iDQp9"
)

# Module-level caches
_skins: dict[str, dict[str, Any]] = {}
_skin_levels_to_skin: dict[str, dict[str, Any]] = {}
_content_tiers: dict[str, dict[str, Any]] = {}
_bundles: dict[str, dict[str, Any]] = {}
_client_version: str = ""


async def initialize() -> None:
    """Fetch all asset data from valorant-api.com. Call once on app startup."""
    global _client_version

    async with httpx.AsyncClient(timeout=30.0) as client:
        skins_resp, tiers_resp, version_resp, bundles_resp = await _fetch_all(client)

    # Skins: index by skin UUID and build level -> skin reverse map
    for skin in skins_resp:
        uuid = skin["uuid"].lower()
        chromas = skin.get("chromas") or []
        levels = skin.get("levels") or []
        skin_entry = {
            "uuid": uuid,
            "displayName": skin.get("displayName", ""),
            "displayIcon": skin.get("displayIcon") or (chromas[0].get("fullRender", "") if chromas else ""),
            "contentTierUuid": (skin.get("contentTierUuid") or "").lower(),
            "levels": levels,
            "chromas": chromas,
            "weapon": skin.get("displayName", "").rsplit(" ", 1)[-1],
        }
        _skins[uuid] = skin_entry

        # Map each level UUID to the parent skin
        for level in levels:
            level_uuid = level["uuid"].lower()
            _skin_levels_to_skin[level_uuid] = skin_entry

    # Content tiers
    for tier in tiers_resp:
        uuid = tier["uuid"].lower()
        _content_tiers[uuid] = {
            "name": tier.get("devName", ""),
            "display_icon": tier.get("displayIcon", ""),
            "highlight_color": tier.get("highlightColor", ""),
        }

    # Bundles
    for bundle in bundles_resp:
        uuid = bundle["uuid"].lower()
        _bundles[uuid] = {
            "uuid": uuid,
            "displayName": bundle.get("displayName", ""),
            "displayIcon": bundle.get("displayIcon") or bundle.get("displayIcon2", ""),
            "description": bundle.get("description", ""),
        }

    # Client version
    _client_version = version_resp.get("riotClientVersion", "")

    logger.info(
        "Asset cache initialized: %d skins, %d levels, %d tiers, %d bundles, version=%s",
        len(_skins),
        len(_skin_levels_to_skin),
        len(_content_tiers),
        len(_bundles),
        _client_version,
    )


async def _fetch_all(client: httpx.AsyncClient) -> tuple[
    list[dict[str, Any]], list[dict[str, Any]], dict[str, Any], list[dict[str, Any]]
]:
    """Fetch all endpoints concurrently."""
    skins_req = client.get(f"{BASE_URL}/weapons/skins")
    tiers_req = client.get(f"{BASE_URL}/contenttiers")
    version_req = client.get(f"{BASE_URL}/version")
    bundles_req = client.get(f"{BASE_URL}/bundles")

    skins_resp, tiers_resp, version_resp, bundles_resp = (
        await skins_req,
        await tiers_req,
        await version_req,
        await bundles_req,
    )

    skins_resp.raise_for_status()
    tiers_resp.raise_for_status()
    version_resp.raise_for_status()
    bundles_resp.raise_for_status()

    return (
        skins_resp.json()["data"],
        tiers_resp.json()["data"],
        version_resp.json()["data"],
        bundles_resp.json()["data"],
    )


def get_skin(uuid: str) -> dict[str, Any] | None:
    """Lookup skin by skin UUID or skin level UUID."""
    key = uuid.lower()
    return _skins.get(key) or _skin_levels_to_skin.get(key)


def get_content_tier(uuid: str) -> dict[str, Any] | None:
    return _content_tiers.get(uuid.lower())


def get_client_version() -> str:
    return _client_version


def get_bundle_info(uuid: str) -> dict[str, Any] | None:
    return _bundles.get(uuid.lower())


def get_skin_preview(uuid: str) -> dict[str, Any] | None:
    """Return cached Riot-hosted preview videos for a skin or skin-level UUID."""
    skin = get_skin(uuid)
    if not skin:
        return None

    def videos(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for ordinal, item in enumerate(items, start=1):
            video = item.get("streamedVideo") or ""
            if not isinstance(video, str) or not video.startswith("https://"):
                continue
            result.append({
                "uuid": str(item.get("uuid", "")).lower(),
                "name": str(item.get("displayName", "")),
                "ordinal": ordinal,
                "streamed_video": video,
                "display_icon": str(item.get("displayIcon") or ""),
                "swatch": str(item.get("swatch") or ""),
                "level_item": str(item.get("levelItem") or ""),
            })
        return result

    return {
        "skin_uuid": skin["uuid"],
        "name": skin.get("displayName", "Unknown skin"),
        "display_icon": skin.get("displayIcon", ""),
        "levels": videos(skin.get("levels") or []),
        "chromas": videos(skin.get("chromas") or []),
    }


def search_skins(query: str = "", weapon: str = "", limit: int = 100) -> list[dict[str, Any]]:
    """Return searchable skin metadata without exposing cache internals."""
    query_key = query.strip().lower()
    weapon_key = weapon.strip().lower()
    results: list[dict[str, Any]] = []
    for skin in _skins.values():
        name = skin.get("displayName", "")
        tier_uuid = skin.get("contentTierUuid", "")
        if not tier_uuid or (query_key and query_key not in name.lower()):
            continue
        if weapon_key and skin.get("weapon", "").lower() != weapon_key:
            continue
        tier = get_content_tier(tier_uuid)
        results.append({
            "uuid": skin["uuid"],
            "name": name,
            "display_icon": skin.get("displayIcon", ""),
            "weapon": skin.get("weapon", ""),
            "content_tier_uuid": tier_uuid,
            "content_tier_name": tier["name"] if tier else "Unknown",
            "content_tier_color": tier["highlight_color"] if tier else "",
        })
    results.sort(key=lambda item: item["name"])
    return results[:limit]
