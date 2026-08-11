import threading
import uuid
from datetime import datetime, timedelta, timezone

from app.models.auth import SessionData

ACCESS_TOKEN_TTL = timedelta(hours=3)
COOKIE_TTL = timedelta(weeks=2)


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, SessionData] = {}
        self._lock = threading.Lock()

    def create(self, data: SessionData) -> str:
        token = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        data.created_at = now
        data.expires_at = now + ACCESS_TOKEN_TTL
        with self._lock:
            self._sessions[token] = data
        return token

    def get(self, token: str) -> SessionData | None:
        with self._lock:
            return self._sessions.get(token)

    def get_or_reauth(self, token: str) -> SessionData | None:
        """Return session data if access token is still valid, None otherwise.

        When None is returned, the caller should attempt cookie reauth
        using the stored riot_cookies (retrievable via get()).
        """
        with self._lock:
            session = self._sessions.get(token)
            if session is None:
                return None
            now = datetime.now(timezone.utc)
            if now >= session.expires_at:
                return None
            return session

    def update(self, token: str, data: SessionData) -> None:
        with self._lock:
            if token in self._sessions:
                self._sessions[token] = data

    def find_active_by_puuid(self, puuid: str) -> SessionData | None:
        now = datetime.now(timezone.utc)
        with self._lock:
            return next((session for session in self._sessions.values() if session.puuid == puuid and now < session.expires_at), None)

    def delete(self, token: str) -> None:
        with self._lock:
            self._sessions.pop(token, None)

    def cleanup(self) -> None:
        """Remove sessions whose riot_cookies have also expired (beyond reauth window)."""
        now = datetime.now(timezone.utc)
        with self._lock:
            expired = [
                token
                for token, session in self._sessions.items()
                if now >= session.created_at + COOKIE_TTL
            ]
            for token in expired:
                del self._sessions[token]


store = SessionStore()
