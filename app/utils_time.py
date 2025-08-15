from datetime import datetime, date, time, timedelta
import zoneinfo
from .config import settings

TZ = zoneinfo.ZoneInfo(settings.CHALLENGE_TZ)

def day_window(d: date):
    start = datetime.combine(d, time(0,0)).replace(tzinfo=TZ)
    end = datetime.combine(d, time(23,59,59)).replace(tzinfo=TZ)
    return start, end

def grace_deadline_for(d: date):
    # Next day at GRACE_CUTOFF_HOUR local
    deadline = datetime.combine(d + timedelta(days=1), time(settings.GRACE_CUTOFF_HOUR,0)).replace(tzinfo=TZ)
    return deadline

def is_early_bird(dt_local: datetime):
    return dt_local.astimezone(TZ).time() < time(7,0)

def is_night_owl(dt_local: datetime):
    return dt_local.astimezone(TZ).time() >= time(22,0)
