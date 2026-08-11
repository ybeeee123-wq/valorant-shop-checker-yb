import httpx


class ReauthenticationRequired(Exception):
    pass


async def fetch_daily_store(base_url: str, device_token: str) -> dict:
    async with httpx.AsyncClient(timeout=40) as client:
        response = await client.get(
            f"{base_url.rstrip('/')}/api/companion/shop",
            headers={"Authorization": f"Bearer {device_token}"},
        )
    if response.status_code == 401:
        raise ReauthenticationRequired("The application session expired")
    response.raise_for_status()
    return response.json()


def sync_payload(daily: dict) -> dict:
    return {
        "seconds_remaining": max(0, int(daily.get("seconds_remaining", 0))),
        "offers": [
            {
                "skin_uuid": offer["uuid"], "skin_name": offer["name"],
                "display_icon": offer.get("display_icon", ""),
                "content_tier_name": offer.get("content_tier_name", "Unknown"),
                "content_tier_color": offer.get("content_tier_color", ""),
                "vp_cost": offer["cost"],
            }
            for offer in daily.get("offers", [])
        ],
    }
