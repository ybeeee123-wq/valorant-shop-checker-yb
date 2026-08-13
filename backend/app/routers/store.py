import json
import logging
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.auth import SessionData
from app.models.persistence import StorefrontState, User
from app.models.store import (
    BundleResponse,
    DailyStoreResponse,
    NightMarketResponse,
    SkinOffer,
    Wallet,
)
from app.routers.auth import authenticated_user
from app.services import storefront
from app.services.cloud import record_snapshot, sync_from_daily
from app.session_store import store

logger = logging.getLogger(__name__)

router = APIRouter()


def _optional_riot_session(request: Request) -> SessionData | None:
    auth = request.headers.get("Authorization", "")
    token = auth[7:] if auth.startswith("Bearer ") else ""
    return store.get_or_reauth(token) if token else None


def _cloud_state(db: Session, user: User) -> StorefrontState:
    state = db.get(StorefrontState, user.id)
    if not state:
        raise HTTPException(
            status_code=409,
            detail="No synced storefront yet. Open VALSHOP Companion and choose Sync Now.",
        )
    return state


def _remaining(state: StorefrontState, value: int) -> int:
    synced_at = state.synced_at
    if synced_at.tzinfo is None:
        synced_at = synced_at.replace(tzinfo=timezone.utc)
    elapsed = int((datetime.now(timezone.utc) - synced_at).total_seconds())
    return max(0, value - max(0, elapsed))


async def get_session(request: Request) -> SessionData:
    """Dependency: extract and validate the session from the Authorization header."""
    auth = request.headers.get("Authorization", "")
    session_token = auth[7:] if auth.startswith("Bearer ") else None

    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    session = store.get_or_reauth(session_token)
    if session:
        return session

    store.delete(session_token)
    raise HTTPException(status_code=401, detail="Session expired. Please log in again.")


def _handle_riot_error(exc: Exception) -> HTTPException:
    """Convert Riot API errors to appropriate HTTP responses."""
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        if status == 400:
            return HTTPException(status_code=502, detail="Riot API rejected the request")
        if status == 403:
            return HTTPException(status_code=502, detail="Access denied by Riot API")
        if status == 404:
            return HTTPException(status_code=502, detail="Store data not found. Is Valorant active on this account?")
        if status == 429:
            return HTTPException(status_code=429, detail="Rate limited by Riot servers. Try again shortly.")
        return HTTPException(status_code=502, detail=f"Riot API error: {status}")
    if isinstance(exc, httpx.RequestError):
        return HTTPException(status_code=502, detail="Could not reach Riot servers")
    return HTTPException(status_code=500, detail="Unexpected error fetching store data")


@router.get("/daily", response_model=DailyStoreResponse)
async def daily_store(
    request: Request,
    user: User = Depends(authenticated_user),
    db: Session = Depends(get_db),
) -> DailyStoreResponse:
    session = _optional_riot_session(request)
    if not session:
        state = _cloud_state(db, user)
        offers = [
            SkinOffer(
                uuid=item["skin_uuid"], name=item["skin_name"],
                display_icon=item.get("display_icon", ""),
                content_tier_uuid=item.get("content_tier_uuid", ""),
                content_tier_name=item.get("content_tier_name", "Unknown"),
                content_tier_color=item.get("content_tier_color", ""),
                cost=item["vp_cost"],
            )
            for item in json.loads(state.offers_json)
        ]
        return DailyStoreResponse(
            offers=offers, seconds_remaining=_remaining(state, state.seconds_remaining)
        )
    try:
        raw = await storefront.fetch_storefront(
            session.access_token, session.entitlements_token, session.puuid, session.shard
        )
    except (httpx.HTTPStatusError, httpx.RequestError) as exc:
        raise _handle_riot_error(exc)
    result = storefront.get_daily_store(raw)
    try:
        record_snapshot(db, user.id, sync_from_daily(result.offers, result.seconds_remaining))
    except Exception:
        logger.exception("Could not persist daily shop snapshot")
    return result


@router.get("/bundle", response_model=BundleResponse)
async def featured_bundle(
    request: Request,
    user: User = Depends(authenticated_user),
    db: Session = Depends(get_db),
) -> BundleResponse:
    session = _optional_riot_session(request)
    if not session:
        state = _cloud_state(db, user)
        bundles = json.loads(state.bundles_json)
        for bundle in bundles:
            bundle["duration_remaining_secs"] = _remaining(
                state, int(bundle.get("duration_remaining_secs", 0))
            )
        return BundleResponse(bundles=bundles)
    try:
        raw = await storefront.fetch_storefront(
            session.access_token, session.entitlements_token, session.puuid, session.shard
        )
    except (httpx.HTTPStatusError, httpx.RequestError) as exc:
        raise _handle_riot_error(exc)
    return storefront.get_featured_bundle(raw)


@router.get("/wallet", response_model=Wallet)
async def wallet(
    request: Request,
    user: User = Depends(authenticated_user),
    db: Session = Depends(get_db),
) -> Wallet:
    session = _optional_riot_session(request)
    if not session:
        return Wallet.model_validate(json.loads(_cloud_state(db, user).wallet_json))
    try:
        return await storefront.get_wallet(
            session.access_token, session.entitlements_token, session.puuid, session.shard
        )
    except (httpx.HTTPStatusError, httpx.RequestError) as exc:
        raise _handle_riot_error(exc)


@router.get("/night-market", response_model=NightMarketResponse)
async def night_market(
    request: Request,
    user: User = Depends(authenticated_user),
    db: Session = Depends(get_db),
) -> NightMarketResponse:
    session = _optional_riot_session(request)
    if not session:
        state = _cloud_state(db, user)
        payload = json.loads(state.night_market_json)
        payload["seconds_remaining"] = _remaining(
            state, int(payload.get("seconds_remaining", 0))
        )
        payload["active"] = bool(payload.get("offers")) or payload["seconds_remaining"] > 0
        return NightMarketResponse.model_validate(payload)
    try:
        raw = await storefront.fetch_storefront(
            session.access_token, session.entitlements_token, session.puuid, session.shard
        )
    except (httpx.HTTPStatusError, httpx.RequestError) as exc:
        raise _handle_riot_error(exc)
    return storefront.get_night_market(raw)
