import httpx
from .config import settings

BASE = "https://www.strava.com/api/v3"

async def exchange_code(code: str):
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post("https://www.strava.com/oauth/token", data={
            "client_id": settings.STRAVA_CLIENT_ID,
            "client_secret": settings.STRAVA_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
        })
        r.raise_for_status()
        return r.json()

async def refresh_token(refresh_token: str):
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post("https://www.strava.com/oauth/token", data={
            "client_id": settings.STRAVA_CLIENT_ID,
            "client_secret": settings.STRAVA_CLIENT_SECRET,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        })
        r.raise_for_status()
        return r.json()

async def get_activity(access_token: str, activity_id: int):
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.get(f"{BASE}/activities/{activity_id}", headers={"Authorization": f"Bearer {access_token}"})
        r.raise_for_status()
        return r.json()

async def list_activities(access_token: str, after_ts: int, before_ts: int):
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(
            "https://www.strava.com/api/v3/athlete/activities",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"after": after_ts, "before": before_ts, "per_page": 200},
        )
        r.raise_for_status()
        return r.json()

async def get_self_profile(access_token: str):
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(
            "https://www.strava.com/api/v3/athlete",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        r.raise_for_status()
        return r.json()