from __future__ import annotations
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from src.app.core.availability import decide_availability
from src.app.core.intent import classify_intent

# ---- Test helpers ----

TZ = ZoneInfo("America/Chicago")


class DummyCfg:
    DEFAULT_TZ = "America/Chicago"
    WORK_HOURS_START = "09:00"
    WORK_HOURS_END = "18:00"
    AVAILABILITY_EDGE_POLICY = "exclusive_end"


def _iso(dt: datetime) -> str:
    return dt.astimezone(TZ).replace(microsecond=0).isoformat()


def _event(title: str, start: datetime, end: datetime, all_day: bool = False):
    return {
        "title": title,
        "start": _iso(start),
        "end": _iso(end),
        "all_day": all_day,
    }


def _today_at(h: int, m: int = 0) -> datetime:
    now = datetime.now(TZ)
    return now.replace(hour=h, minute=m, second=0, microsecond=0)


def _tomorrow_at(h: int, m: int = 0) -> datetime:
    return _today_at(9, 0).replace(hour=h, minute=m) + timedelta(days=1)


# ---- Tests ----

def test_after_time_suggests_earliest_free_segment_today():
    """‘book 30 min after 15:00 today’ returns a 15:00–15:30 slot when free."""
    events = []  # nothing on calendar
    res = decide_availability("book 30 min after 15:00 today", events, DummyCfg)
    assert res.availability == "unknown"  # it's a slot request, not a direct free/busy
    assert res.suggested_slots and len(res.suggested_slots) >= 1

    s0 = datetime.fromisoformat(res.suggested_slots[0]["start"])
    e0 = datetime.fromisoformat(res.suggested_slots[0]["end"])
    assert s0.hour == 15 and s0.minute == 0
    assert (e0 - s0) == timedelta(minutes=30)


def test_after_time_respects_existing_block_and_suggests_next_gap():
    """If 15:00–15:30 is busy, the suggestion should start at 15:30."""
    busy_start = _today_at(15, 0)
    busy_end = _today_at(15, 30)
    events = [_event("standup", busy_start, busy_end)]
    res = decide_availability("book 30 min after 15:00 today", events, DummyCfg)

    assert res.suggested_slots and len(res.suggested_slots) >= 1
    s0 = datetime.fromisoformat(res.suggested_slots[0]["start"])
    e0 = datetime.fromisoformat(res.suggested_slots[0]["end"])
    assert s0.hour == 15 and s0.minute == 30, f"expected 15:30 start, got {s0.time()}"
    assert (e0 - s0) == timedelta(minutes=30)


def test_tomorrow_afternoon_busy_but_suggest_inside_window():
    """
    ‘any slot tomorrow afternoon’ with a 15:00–16:00 meeting should
    report busy AND provide a suggestion in 12:00–17:00 (e.g., 12:00–12:30).
    """
    # Busy tomorrow 15:00–16:00
    t_start = _tomorrow_at(15, 0)
    t_end = _tomorrow_at(16, 0)
    events = [_event("m2 test", t_start, t_end)]

    res = decide_availability("any slot tomorrow afternoon", events, DummyCfg)
    assert res.availability == "busy"
    assert res.conflicts and any(c["title"] == "m2 test" for c in res.conflicts)

    # Should propose something inside 12:00–17:00 that avoids 15:00–16:00
    assert res.suggested_slots is not None
    # Accept either a pre-15:00 suggestion (e.g., 12:00) or post-16:00 (e.g., 16:00)
    s0 = datetime.fromisoformat(res.suggested_slots[0]["start"])
    assert (12 <= s0.hour < 15) or (16 <= s0.hour < 17)


def test_intent_routes_any_slot_to_calendar():
    """Classifier should treat ‘any slot ...’ queries as calendar intent."""
    intent = classify_intent("any slot this fri morning for 45 min")
    assert intent == "calendar"
