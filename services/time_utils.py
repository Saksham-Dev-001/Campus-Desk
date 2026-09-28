"""Indian Standard Time (IST) utilities for CampusDesk.

All dates, timetable schedules, action logs, and uploads in CampusDesk
operate in Indian Standard Time (UTC+05:30).
"""
from datetime import datetime, timezone, timedelta
from typing import Optional

# Indian Standard Time (IST) is fixed at UTC+05:30 (no daylight saving time)
IST = timezone(timedelta(hours=5, minutes=30), name="IST")

def now_ist() -> datetime:
    """Return the current time in Indian Standard Time (IST) as a naive datetime.

    This naive datetime can be directly stored in SQL DateTime columns and
    formatted naturally by Jinja templates.
    """
    return datetime.now(IST).replace(tzinfo=None)

def to_ist(dt: Optional[datetime]) -> Optional[datetime]:
    """Convert any datetime (UTC or aware) into naive IST."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        # If naive and looks like UTC, convert to IST
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(IST).replace(tzinfo=None)

def format_ist(dt: Optional[datetime], fmt: str = "%d %b %Y, %H:%M") -> str:
    """Format a datetime in IST."""
    if not dt:
        return ""
    if dt.tzinfo is not None:
        dt = dt.astimezone(IST).replace(tzinfo=None)
    return dt.strftime(fmt)
