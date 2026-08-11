import json
from typing import Protocol

import keyring

SERVICE = "VALSHOP"
RIOT_SESSION = "riot_session"
CHUNK_SIZE = 900


class CredentialBackend(Protocol):
    def get_password(self, service: str, name: str) -> str | None: ...
    def set_password(self, service: str, name: str, value: str) -> None: ...
    def delete_password(self, service: str, name: str) -> None: ...


class CredentialStore:
    def __init__(self, backend: CredentialBackend = keyring) -> None:
        self.backend = backend

    def save_riot_session(self, session: dict) -> None:
        self.clear_riot_session()
        payload = json.dumps(session, separators=(",", ":"))
        chunks = [payload[index:index + CHUNK_SIZE] for index in range(0, len(payload), CHUNK_SIZE)]
        try:
            for index, chunk in enumerate(chunks):
                self.backend.set_password(SERVICE, f"{RIOT_SESSION}.{index}", chunk)
            self.backend.set_password(
                SERVICE,
                RIOT_SESSION,
                json.dumps({"format": "chunked-v1", "count": len(chunks)}),
            )
        except Exception:
            for index in range(len(chunks)):
                self._delete(f"{RIOT_SESSION}.{index}")
            raise

    def riot_session(self) -> dict | None:
        value = self.backend.get_password(SERVICE, RIOT_SESSION)
        if not value:
            return None
        try:
            metadata = json.loads(value)
        except json.JSONDecodeError:
            return None
        if not isinstance(metadata, dict) or metadata.get("format") != "chunked-v1":
            return metadata
        count = metadata.get("count")
        if not isinstance(count, int) or count < 1 or count > 32:
            return None
        chunks = [
            self.backend.get_password(SERVICE, f"{RIOT_SESSION}.{index}")
            for index in range(count)
        ]
        if any(chunk is None for chunk in chunks):
            return None
        try:
            return json.loads("".join(chunk for chunk in chunks if chunk is not None))
        except json.JSONDecodeError:
            return None

    def clear_riot_session(self) -> None:
        value = self.backend.get_password(SERVICE, RIOT_SESSION)
        try:
            metadata = json.loads(value) if value else {}
        except json.JSONDecodeError:
            metadata = {}
        count = metadata.get("count", 0) if isinstance(metadata, dict) else 0
        if isinstance(count, int):
            for index in range(min(max(count, 0), 32)):
                self._delete(f"{RIOT_SESSION}.{index}")
        self._delete(RIOT_SESSION)

    def save_device_token(self, token: str) -> None:
        self.backend.set_password(SERVICE, "device_token", token)

    def device_token(self) -> str:
        return self.backend.get_password(SERVICE, "device_token") or ""

    def clear_device_token(self) -> None:
        self._delete("device_token")

    def _delete(self, name: str) -> None:
        try:
            self.backend.delete_password(SERVICE, name)
        except keyring.errors.PasswordDeleteError:
            pass
