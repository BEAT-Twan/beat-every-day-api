from fastapi import APIRouter, HTTPException, Query
from .config import settings
from .ingest import handle_strava_event

router = APIRouter(prefix="/webhook")

@router.get("/strava")
async def verify_strava(
    mode: str | None = Query(None, alias="hub.mode"),
    challenge: str | None = Query(None, alias="hub.challenge"),
    verify_token: str | None = Query(None, alias="hub.verify_token"),
):
    if verify_token != settings.STRAVA_VERIFY_TOKEN:
        raise HTTPException(status_code=403, detail="Bad token")
    # Strava expects this exact key back
    return {"hub.challenge": challenge}

@router.post("/strava")
async def receive_event(payload: dict):
    # Strava sends {object_type, object_id, aspect_type, updates, owner_id}
    await handle_strava_event(payload)
    return {"ok": True}
