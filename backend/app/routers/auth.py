import logging
import threading
import time

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.auth import SessionData
from app.models.persistence import User
from app.services import riot_auth
from app.services.cloud import (
    create_web_session,
    get_or_create_user,
    resolve_web_session,
    revoke_web_session,
)
from app.session_store import store

logger = logging.getLogger(__name__)

router = APIRouter()

# --- Rate limiting: 5 requests/minute per IP ---

_rate_lock = threading.Lock()
_rate_log: dict[str, list[float]] = {}
RATE_LIMIT = 5
RATE_WINDOW = 60.0


def _check_rate_limit(ip: str) -> None:
    now = time.monotonic()
    with _rate_lock:
        timestamps = _rate_log.get(ip, [])
        timestamps = [t for t in timestamps if now - t < RATE_WINDOW]
        if len(timestamps) >= RATE_LIMIT:
            raise HTTPException(status_code=429, detail="Too many requests. Try again later.")
        timestamps.append(now)
        _rate_log[ip] = timestamps


def _get_token_from_header(request: Request) -> str | None:
    """Extract session token from Authorization: Bearer <token> header."""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return None


# --- Request/response models ---

class AuthUrlResponse(BaseModel):
    auth_url: str


class TokenSubmitRequest(BaseModel):
    url: str


class LoginResponse(BaseModel):
    status: str  # "success" | "error"
    session_token: str | None = None
    puuid: str | None = None
    error: str | None = None


# --- Endpoints ---

@router.get("/url")
async def get_login_url() -> AuthUrlResponse:
    """Return the Riot OAuth URL for the user to open in their browser."""
    return AuthUrlResponse(auth_url=riot_auth.get_auth_url())


@router.post("/token", response_model=LoginResponse)
async def submit_token(
    body: TokenSubmitRequest, request: Request, db: Session = Depends(get_db)
) -> LoginResponse:
    """Accept the pasted redirect URL, extract tokens, and create a session."""
    _check_rate_limit(request.client.host if request.client else "unknown")

    try:
        tokens = riot_auth.extract_tokens(body.url)
        access_token = tokens["access_token"]
        id_token = tokens.get("id_token", "")

        entitlements = await riot_auth.get_entitlements(access_token)
        puuid = await riot_auth.get_player_info(access_token)
        region, shard = await riot_auth.get_region(access_token, id_token)

        session_data = SessionData(
            access_token=access_token,
            entitlements_token=entitlements,
            puuid=puuid,
            shard=shard,
            region=region,
        )
        session_token = store.create(session_data)
        user = get_or_create_user(db, puuid)
        create_web_session(db, user.id, session_token)

        return LoginResponse(status="success", session_token=session_token, puuid=puuid)

    except riot_auth.AuthenticationError as e:
        return LoginResponse(status="error", error=str(e))
    except riot_auth.RateLimitError:
        return LoginResponse(status="error", error="Rate limited by Riot servers. Try again shortly.")
    except httpx.HTTPStatusError as e:
        logger.error("Riot API HTTP error: %s", e.response.status_code)
        return LoginResponse(status="error", error=f"Riot API error ({e.response.status_code})")
    except httpx.RequestError as e:
        logger.error("Network error contacting Riot: %s", e)
        return LoginResponse(status="error", error="Could not reach Riot servers. Try again.")
    except Exception:
        logger.exception("Token submission failed")
        return LoginResponse(status="error", error="Authentication failed unexpectedly")


@router.post("/logout")
async def logout(request: Request, db: Session = Depends(get_db)) -> dict:
    token = _get_token_from_header(request)
    if token:
        store.delete(token)
        revoke_web_session(db, token)
    return {"status": "ok"}


@router.get("/session")
async def check_session(request: Request, db: Session = Depends(get_db)) -> dict:
    token = _get_token_from_header(request)
    if not token:
        return {"valid": False}

    session = store.get_or_reauth(token)
    if session:
        return {"valid": True, "puuid": session.puuid}

    web_session = resolve_web_session(db, token)
    user = db.get(User, web_session.user_id) if web_session else None
    if not user:
        return {"valid": False}

    return {"valid": True, "puuid": user.puuid}


def authenticated_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = _get_token_from_header(request)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    riot_session = store.get_or_reauth(token)
    if riot_session:
        return get_or_create_user(db, riot_session.puuid)
    web_session = resolve_web_session(db, token)
    user = db.get(User, web_session.user_id) if web_session else None
    if not user:
        raise HTTPException(status_code=401, detail="Session expired. Please log in again.")
    return user
