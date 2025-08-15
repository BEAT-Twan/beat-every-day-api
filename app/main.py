from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from datetime import date as ddate
from fastapi.responses import RedirectResponse
from .config import settings
from .db import engine, get_session
from . import models
from .webhook import router as webhook_router
from .rollup import compute_day
from .strava import exchange_code
from .models import Participant, Activity, Points, DailyRollup
from sqlalchemy import text
from .security import require_admin
from httpx import HTTPStatusError
from .strava import refresh_token, list_activities, get_self_profile
from .classify import is_cycling, is_ebike

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="BEAT Every Day API")
app.include_router(webhook_router)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/leaderboard")
def leaderboard(date: str, db: Session = Depends(get_session)):
    # parse YYYY-MM-DD strictly
    try:
        target = ddate.fromisoformat(date)
    except Exception:
        raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD")

    rows = db.execute(
        text("""
            WITH dr_day AS (
              SELECT * FROM daily_rollups WHERE date = :d
            ),
            -- All streak groups up to :d (met_25km days only)
            ds AS (
              SELECT athlete_id, date
              FROM daily_rollups
              WHERE date <= :d AND met_25km = TRUE
            ),
            numbered AS (
              SELECT athlete_id, date,
                     ROW_NUMBER() OVER (PARTITION BY athlete_id ORDER BY date) AS rn
              FROM ds
            ),
            grouped AS (
              SELECT athlete_id, date,
                     (date::timestamp - (rn || ' day')::interval) AS grp
              FROM numbered
            ),
            streaks AS (
              SELECT athlete_id,
                     MIN(date) AS s_start,
                     MAX(date) AS s_end,
                     COUNT(*)  AS len
              FROM grouped
              GROUP BY athlete_id, grp
            ),
            -- current streak = ends on :d
            current_streak AS (
              SELECT athlete_id, s_start, s_end, len
              FROM streaks
              WHERE s_end = :d
            ),
            -- longest streak up to :d (break ties by most recent end)
            longest_streak AS (
              SELECT DISTINCT ON (athlete_id)
                     athlete_id, s_start, LEAST(s_end, :d) AS s_end, len
              FROM streaks
              ORDER BY athlete_id, len DESC, s_end DESC
            ),
            -- sums within the current streak window (if any)
            current_sums AS (
              SELECT dr.athlete_id,
                     SUM(dr.km_total)   AS cur_km_total,
                     SUM(dr.km_outdoor) AS cur_km_outdoor
              FROM daily_rollups dr
              JOIN current_streak cs
                ON cs.athlete_id = dr.athlete_id
               AND dr.date BETWEEN cs.s_start AND cs.s_end
              GROUP BY dr.athlete_id
            ),
            -- sums within the longest streak window
            longest_sums AS (
              SELECT dr.athlete_id,
                     SUM(dr.km_total)   AS longest_km_total,
                     SUM(dr.km_outdoor) AS longest_km_outdoor
              FROM daily_rollups dr
              JOIN longest_streak ls
                ON ls.athlete_id = dr.athlete_id
               AND dr.date BETWEEN ls.s_start AND ls.s_end
              GROUP BY dr.athlete_id
            )
            SELECT
              dr.athlete_id,
              -- per-day (added today)
              dr.km_total     AS added_km_total,
              dr.km_outdoor   AS added_km_outdoor,
              dr.km_indoor,
              dr.met_25km,
              dr.first_start_time_local,
              dr.early_bird,
              dr.night_owl,
              -- points as before
              COALESCE(p.cumulative_points, 0) AS cumulative_points,
              -- current streak (ending on :d)
              COALESCE(cs.len, 0)              AS streak,
              COALESCE(cur.cur_km_total, 0)    AS current_km_total,
              COALESCE(cur.cur_km_outdoor, 0)  AS current_km_outdoor,
              -- longest streak window
              COALESCE(ls.len, 0)              AS longest_streak_len,
              COALESCE(lgs.longest_km_total, 0)   AS longest_km_total,
              COALESCE(lgs.longest_km_outdoor, 0) AS longest_km_outdoor
            FROM dr_day dr
            LEFT JOIN points p
              ON p.athlete_id = dr.athlete_id AND p.date = dr.date
            LEFT JOIN current_streak cs
              ON cs.athlete_id = dr.athlete_id
            LEFT JOIN current_sums cur
              ON cur.athlete_id = dr.athlete_id
            LEFT JOIN longest_streak ls
              ON ls.athlete_id = dr.athlete_id
            LEFT JOIN longest_sums lgs
              ON lgs.athlete_id = dr.athlete_id
            ORDER BY p.cumulative_points DESC NULLS LAST, dr.km_total DESC
        """),
        {"d": target},
    ).mappings().all()

    return {"date": str(target), "rows": rows}

@app.post("/admin/recompute")
async def admin_recompute(
    d: str,
    _: None = Depends(require_admin),
    db: Session = Depends(get_session),
):
    from datetime import date as ddate  # ensure alias in this scope
    compute_day(db, ddate.fromisoformat(d))
    return {"ok": True}

@app.post("/admin/participants/refresh_names")
async def refresh_names(_=Depends(require_admin), db: Session = Depends(get_session)):
    updated = 0
    for p in db.query(Participant).filter(Participant.strava_access_token.isnot(None)).all():
        try:
            prof = await get_self_profile(p.strava_access_token)
        except HTTPStatusError as e:
            if e.response.status_code == 401 and p.strava_refresh_token:
                new = await refresh_token(p.strava_refresh_token)
                p.strava_access_token = new["access_token"]
                p.strava_refresh_token = new.get("refresh_token", p.strava_refresh_token)
                p.strava_token_expires_at = new.get("expires_at", p.strava_token_expires_at)
                db.add(p); db.commit()
                prof = await get_self_profile(p.strava_access_token)
            else:
                continue

        full = f"{(prof.get('firstname') or '').strip()} {(prof.get('lastname') or '').strip()}".strip()
        username = prof.get('username')
        new_name = full or username or f"Strava #{p.strava_athlete_id}"
        if new_name and new_name != (p.name or ""):
            p.name = new_name
            db.add(p); updated += 1

    db.commit()
    return {"ok": True, "updated": updated}

@app.get("/auth/strava/start")
async def auth_start():
    scopes = "read,activity:read,activity:read_all"
    url = (
        "https://www.strava.com/oauth/authorize?"
        f"client_id={settings.STRAVA_CLIENT_ID}&response_type=code&redirect_uri={settings.STRAVA_REDIRECT_URI}"
        f"&approval_prompt=auto&scope={scopes}"
    )
    return RedirectResponse(url)

@app.get("/auth/strava/callback")
async def auth_cb(code: str, state: str | None = None, db: Session = Depends(get_session)):
    token = await exchange_code(code)
    athlete = token["athlete"]
    p = db.query(Participant).filter_by(strava_athlete_id=athlete["id"]).first()
    if not p:
        p = Participant(strava_athlete_id=athlete["id"], name=f"{athlete['firstname']} {athlete['lastname']}")
    p.strava_access_token = token["access_token"]
    p.strava_refresh_token = token["refresh_token"]
    p.strava_token_expires_at = token["expires_at"]
    # after you get `athlete` dict:
    full = f"{(athlete.get('firstname') or '').strip()} {(athlete.get('lastname') or '').strip()}".strip()
    username = athlete.get('username')
    p.name = full or username or f"Strava #{athlete['id']}"

    db.add(p)
    db.commit()
    return {"ok": True, "message": "Strava connected"}

@app.get("/participants")
def participants(db: Session = Depends(get_session)):
    out = []
    for p in db.query(Participant).all():
        # prefer p.name; fall back safely
        nm = getattr(p, "name", None) or f"Strava #{getattr(p,'strava_athlete_id', '???')}"
        out.append({"id": p.id, "name": nm})
    return out

@app.post("/admin/backfill")
async def admin_backfill(
    days: int = 3,
    _: None = Depends(require_admin),
    db: Session = Depends(get_session),
):
    since = datetime.now(timezone.utc) - timedelta(days=days)
    before = datetime.now(timezone.utc) + timedelta(days=1)
    after_ts = int(since.timestamp())
    before_ts = int(before.timestamp())

    participants = db.query(Participant).filter(Participant.strava_access_token.isnot(None)).all()
    for p in participants:
        token = p.strava_access_token
        try:
            acts = await list_activities(token, after_ts, before_ts)
        except HTTPStatusError as e:
            if e.response.status_code == 401 and p.strava_refresh_token:
                new = await refresh_token(p.strava_refresh_token)
                p.strava_access_token = new["access_token"]
                p.strava_refresh_token = new.get("refresh_token", p.strava_refresh_token)
                p.strava_token_expires_at = new.get("expires_at", p.strava_token_expires_at)
                db.add(p); db.commit()
                acts = await list_activities(p.strava_access_token, after_ts, before_ts)
            else:
                continue

        for a in acts:
            sport = a.get("sport_type") or a.get("type")
            if not is_cycling(sport) and not is_ebike(sport):
                continue

            rec = db.query(Activity).filter_by(source="strava", strava_activity_id=a["id"]).first()
            if not rec:
                rec = Activity(source="strava", strava_activity_id=a["id"], athlete_id=p.id)

            sdl = a["start_date_local"].replace("Z", "+00:00")
            rec.start_date_local = datetime.fromisoformat(sdl)
            rec.distance_m = float(a.get("distance") or 0)
            rec.moving_time_s = int(a.get("moving_time") or 0)
            rec.sport_type = sport
            rec.trainer = bool(a.get("trainer"))
            rec.is_virtual = (sport == "VirtualRide")
            rec.is_ebike = (sport == "EBikeRide")
            db.add(rec)

        db.commit()

    return {"ok": True, "days": days}

@app.post("/admin/participants/{pid}/rename")
def rename_participant(
    pid: int,
    name: str,
    _: None = Depends(require_admin),
    db: Session = Depends(get_session),
):
    p = db.query(Participant).get(pid)
    if not p:
        raise HTTPException(404, "participant not found")
    p.display_name = name
    db.add(p); db.commit()
    return {"ok": True, "id": p.id, "name": p.display_name}
