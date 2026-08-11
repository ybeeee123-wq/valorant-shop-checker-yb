import asyncio
import hashlib
import secrets
import urllib.parse
import webbrowser

import httpx

from credentials import CredentialStore


class PairingClient:
    def __init__(self, api_url: str, site_url: str, credentials: CredentialStore) -> None:
        self.api_url = api_url.rstrip("/")
        self.site_url = site_url.rstrip("/")
        self.credentials = credentials

    async def pair(self, device_name: str, timeout_seconds: int = 600) -> str:
        challenge = secrets.token_urlsafe(48)
        verifier = secrets.token_urlsafe(48)
        verifier_hash = hashlib.sha256(verifier.encode()).hexdigest()
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(f"{self.api_url}/api/companion/pairing/start", json={"challenge": challenge, "verifier_hash": verifier_hash, "device_name": device_name})
            response.raise_for_status()
        webbrowser.open(f"{self.site_url}/connect-companion?{urllib.parse.urlencode({'challenge': challenge})}")
        elapsed = 0
        while elapsed < timeout_seconds:
            await asyncio.sleep(3); elapsed += 3
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.post(f"{self.api_url}/api/companion/pairing/poll", json={"challenge": challenge, "verifier": verifier})
            response.raise_for_status()
            data = response.json()
            if data["status"] == "approved" and data.get("device_token"):
                self.credentials.save_device_token(data["device_token"])
                return data["device_token"]
            if data["status"] == "expired":
                break
        raise RuntimeError("Pairing expired. Start the connection again.")
