from datetime import datetime
from .db import session_scope
from .models import Participant, Activity
from .strava import get_activity
from .classify import is_cycling, is_ebike

async def handle_strava_event(payload: dict):
    if payload.get("object_type") != "activity":
        return
    activity_id = int(payload["object_id"])
    owner_id = int(payload["owner_id"])  # strava athlete id

    # lookup participant
    with session_scope() as db:
        p = db.query(Participant).filter_by(strava_athlete_id=owner_id).first()
        if not p or not p.strava_access_token:
            return

        data = await get_activity(p.strava_access_token, activity_id)
        # filter
        sport = data.get("sport_type") or data.get("type")
        if not is_cycling(sport) and not is_ebike(sport):
            return

        a = db.query(Activity).filter_by(source="strava", strava_activity_id=activity_id).first()
        if not a:
            a = Activity(source="strava", strava_activity_id=activity_id, athlete_id=p.id)

        # Strava returns ISO8601; ensure timezone-aware
        start_local_raw = data.get("start_date_local") or data.get("start_date")
        a.start_date_local = datetime.fromisoformat(start_local_raw.replace("Z", "+00:00"))
        a.distance_m = float(data.get("distance") or 0)
        a.moving_time_s = int(data.get("moving_time") or 0)
        a.sport_type = sport
        a.trainer = bool(data.get("trainer"))
        a.is_virtual = (sport == "VirtualRide")
        a.is_ebike = is_ebike(sport)
        a.raw_json = None  # optionally json.dumps(data)

        db.add(a)
        db.commit()
