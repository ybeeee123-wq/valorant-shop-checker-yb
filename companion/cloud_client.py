import httpx


class CloudClient:
    def __init__(self, base_url: str, device_token: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.headers = {"Authorization": f"Bearer {device_token}"}

    async def heartbeat(self, reauth_required: bool = False) -> None:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(f"{self.base_url}/api/companion/heartbeat", headers=self.headers, json={"reauth_required": reauth_required})
            response.raise_for_status()

    async def sync(self, payload: dict) -> dict:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(f"{self.base_url}/api/companion/shop-sync", headers=self.headers, json=payload)
            response.raise_for_status()
            return response.json()

    async def wishlist(self) -> list[dict]:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(f"{self.base_url}/api/companion/wishlist", headers=self.headers)
            response.raise_for_status(); return response.json()

    async def add_wishlist(self, skin_uuid: str) -> dict:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(f"{self.base_url}/api/companion/wishlist", headers=self.headers, json={"skin_uuid": skin_uuid})
            response.raise_for_status(); return response.json()

    async def remove_wishlist(self, skin_uuid: str) -> None:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.delete(f"{self.base_url}/api/companion/wishlist/{skin_uuid}", headers=self.headers)
            response.raise_for_status()

    async def history(self) -> list[dict]:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(f"{self.base_url}/api/companion/history", headers=self.headers)
            response.raise_for_status(); return response.json()

    async def revoke(self) -> None:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.delete(f"{self.base_url}/api/companion/self", headers=self.headers)
            response.raise_for_status()
