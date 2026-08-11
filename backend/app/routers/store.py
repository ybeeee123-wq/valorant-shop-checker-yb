import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request

from app.database import SessionLocal
from app.models.auth import SessionData
from app.models.store import BundleResponse, DailyStoreResponse, NightMarketResponse, Wallet
from app.services import storefront
from app.services.cloud import get_or_create_user, record_snapshot, sync_from_daily
from app.session_store import store

logger = logging.getLogger(__name__)

router = APIRouter()


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
async def daily_store(session: SessionData = Depends(get_session)) -> DailyStoreResponse:
    try:
        raw = await storefront.fetch_storefront(
            session.access_token, session.entitlements_token, session.puuid, session.shard
        )
    except (httpx.HTTPStatusError, httpx.RequestError) as exc:
        raise _handle_riot_error(exc)
    result = storefront.get_daily_store(raw)
    db = SessionLocal()
    try:
        user = get_or_create_user(db, session.puuid)
        record_snapshot(db, user.id, sync_from_daily(result.offers, result.seconds_remaining))
    except Exception:
        logger.exception("Could not persist daily shop snapshot")
    finally:
        db.close()
    return result


@router.get("/bundle", response_model=BundleResponse)
async def featured_bundle(session: SessionData = Depends(get_session)) -> BundleResponse:
    try:
        raw = await storefront.fetch_storefront(
            session.access_token, session.entitlements_token, session.puuid, session.shard
        )
    except (httpx.HTTPStatusError, httpx.RequestError) as exc:
        raise _handle_riot_error(exc)
    return storefront.get_featured_bundle(raw)


@router.get("/wallet", response_model=Wallet)
async def wallet(session: SessionData = Depends(get_session)) -> Wallet:
    try:
        return await storefront.get_wallet(
            session.access_token, session.entitlements_token, session.puuid, session.shard
        )
    except (httpx.HTTPStatusError, httpx.RequestError) as exc:
        raise _handle_riot_error(exc)


@router.get("/night-market", response_model=NightMarketResponse)
async def night_market(session: SessionData = Depends(get_session)) -> NightMarketResponse:
    try:
        raw = await storefront.fetch_storefront(
            session.access_token, session.entitlements_token, session.puuid, session.shard
        )
    except (httpx.HTTPStatusError, httpx.RequestError) as exc:
        raise _handle_riot_error(exc)
    return storefront.get_night_market(raw)
