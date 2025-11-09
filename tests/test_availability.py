# tests/test_availability.py
from __future__ import annotations
import sys, pathlib
from datetime import datetime, timedelta
import pytest

# Make 'src' importable when running pytest from repo root
ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from app.core.availability import decide_availability  # type: ignore
from app.core.timeparse import parse_query_to_windows  # type: ignore

class DummyCfg:
    DEFAULT_TZ = "America/Chicago"
    WORK_HOURS_START = "09:00"
    WORK_HOURS_END = "18:00"
    AVAILABILITY_EDGE_POLICY = "exclusive_end"

def _iso(dt: datetime) -> str:
    # Ensure ISO with tz offset
    return dt.replace(microsecond=0).isoformat()

def _tomorrow_at(h: int, m: int = 0):
    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo(DummyCfg.DEFAULT_TZ)
        now = datetime.now(tz)
    except Exception:
        from dateutil.tz import tzlocal
        tz = tzlocal()
        now = datetime.now(tz)
    base = (now + timedelta(days=1)).replace(second=0, microsecond=0)
    return base.replace(hour=h, minute=m)

def _event(title: str, start: datetime, end: datetime, all_day: bool = False):
    return {
        "title": title,
        "start": _iso(start),
        "end": _iso(end),
        "all_day": all_day,
    }

def test_busy_at_tomorrow_10_point_check():
    # Event 10:00–11:00 tomorrow → query "tomorrow at 10" should be busy
    s = _tomorrow_at(10, 0)
    e = _tomorrow_at(11, 0)
    events = [_event("Project Sync", s, e)]
    res = decide_availability("am I free tomorrow at 10?", events, DummyCfg)
    assert res.availability == "busy"
    assert res.conflicts and res.conflicts[0]["title"] == "Project Sync"

def test_free_at_tomorrow_11_boundary_exclusive():
    # Back-to-back boundary: event 10–11, query 11:00 should be free (exclusive end)
    s = _tomorrow_at(10, 0)
    e = _tomorrow_at(11, 0)
    events = [_event("Standup", s, e)]
    res = decide_availability("am I free tomorrow at 11?", events, DummyCfg)
    assert res.availability == "free"

def test_all_day_blocks_daypart():
    # All-day event tomorrow blocks "tomorrow afternoon"
    t_start = _tomorrow_at(0, 0)
    t_end = _tomorrow_at(0, 0) + timedelta(days=1)
    events = [_event("OOO", t_start, t_end, all_day=True)]
    res = decide_availability("tomorrow afternoon", events, DummyCfg)
    assert res.availability == "busy"
