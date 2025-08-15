from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import func, case, and_
from .models import Activity, DailyRollup, Points, Award
from .utils_time import day_window, is_early_bird, is_night_owl, TZ

KM = 1000.0

def compute_day(db: Session, d: date):
    start, end = day_window(d)

    indoor_expr = ( (Activity.is_virtual == True) | (Activity.trainer == True) )
    dist_indoor = func.sum(case((indoor_expr, Activity.distance_m), else_=0.0))
    dist_outdoor = func.sum(case((indoor_expr, 0.0), else_=Activity.distance_m))

    rows = db.query(
        Activity.athlete_id,
        func.sum(Activity.distance_m).label("dist"),
        dist_indoor.label("dist_indoor"),
        func.min(Activity.start_date_local).label("first_start"),
        dist_outdoor.label("dist_outdoor"),
    ).filter(
        Activity.start_date_local >= start,
        Activity.start_date_local <= end,
        Activity.is_ebike == False,
    ).group_by(Activity.athlete_id).all()

    # Upsert rollups
    for r in rows:
        roll = db.query(DailyRollup).filter_by(athlete_id=r.athlete_id, date=d).first()
        if not roll:
            roll = DailyRollup(athlete_id=r.athlete_id, date=d)
        roll.km_total = (r.dist or 0) / KM
        roll.km_indoor = (r.dist_indoor or 0) / KM
        roll.km_outdoor = (r.dist_outdoor or 0) / KM
        roll.met_25km = roll.km_total >= 25
        roll.first_start_time_local = r.first_start
        roll.early_bird = bool(r.first_start and is_early_bird(r.first_start.astimezone(TZ)))
        roll.night_owl = bool(r.first_start and is_night_owl(r.first_start.astimezone(TZ)))
        db.add(roll)
    db.commit()

    # Awards (example: longest indoor/outdoor)
    top_out = db.query(DailyRollup).filter_by(date=d).order_by(DailyRollup.km_outdoor.desc()).first()
    top_in = db.query(DailyRollup).filter_by(date=d).order_by(DailyRollup.km_indoor.desc()).first()
    if top_out:
        db.add(Award(date=d, category="road_warrior", athlete_id=top_out.athlete_id, value_num=top_out.km_outdoor))
    if top_in:
        db.add(Award(date=d, category="zwift_warrior", athlete_id=top_in.athlete_id, value_num=top_in.km_indoor))
    db.commit()

    # Points (idempotent upsert)
    for roll in db.query(DailyRollup).filter_by(date=d).all():
        pts = 0
        if roll.km_total >= 25: pts += 5
        if roll.km_total >= 100: pts += 5
        if roll.km_outdoor >= 25: pts += 2
        if roll.km_indoor >= 25: pts += 2
        if roll.early_bird: pts += 1
        if roll.night_owl: pts += 1

        # previous day's cumulative (exclude same day)
        prev = (
            db.query(Points)
            .filter(Points.athlete_id == roll.athlete_id, Points.date < d)
            .order_by(Points.date.desc())
            .first()
        )
        cumulative = (prev.cumulative_points if prev else 0) + pts

        p_day = db.query(Points).filter_by(athlete_id=roll.athlete_id, date=d).first()
        if not p_day:
            p_day = Points(date=d, athlete_id=roll.athlete_id)

        p_day.daily_points = pts
        p_day.cumulative_points = cumulative
        db.add(p_day)

    db.commit()

