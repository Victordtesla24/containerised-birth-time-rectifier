from datetime import datetime, time
from zoneinfo import ZoneInfo
import pytz

def convert_time_to_utc(local_time: time, date: datetime, timezone: str) -> time:
    """Convert a local time to UTC time."""
    local_dt = datetime.combine(date, local_time)
    local_dt = local_dt.replace(tzinfo=ZoneInfo(timezone))
    utc_dt = local_dt.astimezone(pytz.UTC)
    return utc_dt.time()

def convert_time_from_utc(utc_time: time, date: datetime, timezone: str) -> time:
    """Convert a UTC time to local time."""
    utc_dt = datetime.combine(date, utc_time)
    utc_dt = utc_dt.replace(tzinfo=pytz.UTC)
    local_dt = utc_dt.astimezone(ZoneInfo(timezone))
    return local_dt.time()

def get_timezone_offset(timezone: str) -> float:
    """Get the current offset of a timezone in hours."""
    now = datetime.now(ZoneInfo(timezone))
    return now.utcoffset().total_seconds() / 3600

def validate_timezone(timezone: str) -> bool:
    """Validate if a timezone string is valid."""
    try:
        ZoneInfo(timezone)
        return True
    except Exception:
        return False 