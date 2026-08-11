from datetime import datetime, timedelta, timezone

import httpx

from app.services import asset_cache, riot_auth, storefront
from credentials import CredentialStore


class RiotConnectionExpired(RuntimeError):
    pass


class LocalRiotClient:
    def __init__(self, credentials: CredentialStore) -> None:
        self.credentials = credentials
        self.session: dict | None = credentials.riot_session()
        self.assets_ready = False

    async def initialize_assets(self) -> None:
        if not self.assets_ready:
            await asset_cache.initialize()
            self.assets_ready = True

    async def connect(self, callback_url: str) -> dict:
        tokens = riot_auth.extract_tokens(callback_url)
        access_token = tokens["access_token"]
        entitlements = await riot_auth.get_entitlements(access_token)
        puuid = await riot_auth.get_player_info(access_token)
        region, shard = await riot_auth.get_region(access_token, tokens.get("id_token", ""))
        self.session = {
            "access_token": access_token,
            "entitlements_token": entitlements,
            "puuid": puuid,
            "region": region,
            "shard": shard,
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=3)).isoformat(),
        }
        self.credentials.save_riot_session(self.session)
        return {"puuid": puuid, "region": region}

    async def validate(self) -> bool:
        if not self.session:
            return False
        try:
            expires = datetime.fromisoformat(self.session["expires_at"])
            if expires <= datetime.now(timezone.utc):
                return False
            return await riot_auth.get_player_info(self.session["access_token"]) == self.session["puuid"]
        except (KeyError, ValueError, httpx.HTTPError):
            return False

    async def fetch_shop(self) -> dict:
        if not self.session or not await self.validate():
            raise RiotConnectionExpired("Reconnect Riot to continue checking your shop.")
        await self.initialize_assets()
        try:
            raw = await storefront.fetch_storefront(
                self.session["access_token"], self.session["entitlements_token"],
                self.session["puuid"], self.session["shard"],
            )
            daily = storefront.get_daily_store(raw)
            bundles = storefront.get_featured_bundle(raw)
            night_market = storefront.get_night_market(raw)
            wallet = await storefront.get_wallet(
                self.session["access_token"], self.session["entitlements_token"],
                self.session["puuid"], self.session["shard"],
            )
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in {401, 403}:
                raise RiotConnectionExpired("Riot connection expired") from exc
            raise
        reset = datetime.now(timezone.utc) + timedelta(seconds=daily.seconds_remaining)
        return {
            "rotation_key": reset.strftime("%Y%m%dT%H%MZ"),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "seconds_remaining": daily.seconds_remaining,
            "offers": [offer.model_dump() for offer in daily.offers],
            "bundles": bundles.model_dump()["bundles"],
            "night_market": night_market.model_dump(),
            "wallet": wallet.model_dump(),
        }

    def disconnect(self) -> None:
        self.session = None
        self.credentials.clear_riot_session()
