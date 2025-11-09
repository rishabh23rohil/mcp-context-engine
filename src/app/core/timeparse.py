from __future__ import annotations
import re
from datetime import datetime, timedelta, time
from typing import List, Tuple, Optional, Dict, Any
from zoneinfo import ZoneInfo

_DAY_MAP = {
    "mon": 0, "tue": 1, "wed": 2, "thu": 3, "thur": 3, "thurs": 3,
    "fri": 4, "sat": 5, "sun": 6
}

def _next_weekday(base: datetime, target_wd: int) -> datetime:
    days_ahead = (target_wd - base.weekday() + 7) % 7
    if days_ahead == 0:
        days_ahead = 7
    return base + timedelta(days=days_ahead)

def _parse_24h(hh: int, mm: int) -> time:
    hh = max(0, min(23, hh))
    mm = max(0, min(59, mm))
    return time(hh, mm, 0)

def _daypart_bounds(label: str) -> tuple[time, time]:
    label = label.lower()
    if label == "morning":
        return time(9, 0), time(12, 0)
    if label == "afternoon":
        return time(12, 0), time(17, 0)
    if label == "evening":
        return time(17, 0), time(21, 0)
    return time(9, 0), time(18, 0)

# -----------------------
# Availability windows (was already used by M3 free/busy)
# -----------------------
def parse_query_to_windows(text: str, tz: ZoneInfo, cfg=None) -> List[Tuple[datetime, datetime]]:
    """
    Strict 24h clock.

    Handles:
      - "tomorrow 15:10", "today 08:00"
      - "next thu 14-15"
      - "today afternoon", "tomorrow morning"
      - "at 23" (today point)
    """
    now = datetime.now(tz)
    s = text.strip().lower()

    # today/tomorrow + hh[:mm]
    m = re.search(r"\b(tomorrow|today)\s+(?:at\s+)?(\d{1,2})(?::(\d{2}))?\b", s)
    if m:
        day_word, hh, mm = m.group(1), int(m.group(2)), int(m.group(3) or 0)
        base = now if day_word == "today" else now + timedelta(days=1)
        t = _parse_24h(hh, mm)
        start = base.replace(hour=t.hour, minute=t.minute, second=0, microsecond=0)
        return [(start, start)]

    # next <weekday> hh-hh(:mm)?
    m = re.search(
        r"\bnext\s+(mon|tue|wed|thu|thur|thurs|fri|sat|sun)\s+"
        r"(\d{1,2})(?::(\d{2}))?\s*[–-]\s*(\d{1,2})(?::(\d{2}))?\b",
        s
    )
    if m:
        wd, h1, m1, h2, m2 = (
            m.group(1),
            int(m.group(2)), int(m.group(3) or 0),
            int(m.group(4)), int(m.group(5) or 0),
        )
        target_day = _next_weekday(now, _DAY_MAP[wd])
        t1 = _parse_24h(h1, m1)
        t2 = _parse_24h(h2, m2)
        start = target_day.replace(hour=t1.hour, minute=t1.minute, second=0, microsecond=0)
        end = target_day.replace(hour=t2.hour, minute=t2.minute, second=0, microsecond=0)
        if end < start:
            end = start
        return [(start, end)]

    # (today|tomorrow) <daypart>
    m = re.search(r"\b(today|tomorrow)\s+(morning|afternoon|evening)\b", s)
    if m:
        day_word, label = m.group(1), m.group(2)
        base = now if day_word == "today" else now + timedelta(days=1)
        t1, t2 = _daypart_bounds(label)
        start = base.replace(hour=t1.hour, minute=t1.minute, second=0, microsecond=0)
        end = base.replace(hour=t2.hour, minute=t2.minute, second=0, microsecond=0)
        return [(start, end)]

    # "at hh[:mm]" (today point)
    m = re.search(r"\bat\s+(\d{1,2})(?::(\d{2}))?\b", s)
    if m:
        hh, mm = int(m.group(1)), int(m.group(2) or 0)
        t = _parse_24h(hh, mm)
        start = now.replace(hour=t.hour, minute=t.minute, second=0, microsecond=0)
        return [(start, start)]

    return []

# -----------------------
# Slot-finding intents (new)
# -----------------------
def parse_slot_intent(text: str, tz: ZoneInfo) -> Optional[Dict[str, Any]]:
    """
    Detect 'find me a slot' requests and return a structured request.

    Supported (24h):
      - "book 30 min after 15:00 today"
      - "book 30 minutes after today 15:00"
      - "book 45 m after 9"
      - "any slot this fri morning"
      - "any slot tomorrow afternoon for 60 min"
    """
    s = text.strip().lower()
    now = datetime.now(tz)

    # -------- Order-agnostic "after <time> [today|tomorrow]" --------
    # First, ensure it's a booking-style command with a duration.
    dur_m = re.search(r"\b(?:book|find|schedule)\s+(\d{1,3})\s*(?:min(?:ute)?s?|m)\b", s)
    after_m = re.search(r"\bafter\b", s)
    if dur_m and after_m:
        dur = int(dur_m.group(1))
        tail = s[after_m.end():].strip()  # text after "after"

        # Accept either "15[:00] [today|tomorrow]" OR "(today|tomorrow) 15[:00]"
        # pattern A: time first, optional dayword after
        mA = re.search(r"^\s*(\d{1,2})(?::(\d{2}))?(?:\s+(today|tomorrow))?\b", tail)
        # pattern B: dayword first, then time
        mB = re.search(r"^\s*(today|tomorrow)\s+(\d{1,2})(?::(\d{2}))?\b", tail)

        if mA or mB:
            if mA:
                hh = int(mA.group(1)); mm = int(mA.group(2) or 0)
                day_word = mA.group(3)
            else:
                day_word = mB.group(1)
                hh = int(mB.group(2)); mm = int(mB.group(3) or 0)

            base = now if (not day_word or day_word == "today") else now + timedelta(days=1)
            t = _parse_24h(hh, mm)
            after_dt = base.replace(hour=t.hour, minute=t.minute, second=0, microsecond=0)
            return {"mode": "after_time", "after": after_dt, "duration_min": dur}

        # Fallback: allow just "after 9" with no dayword
        mC = re.search(r"^\s*(\d{1,2})(?::(\d{2}))?\b", tail)
        if mC:
            hh = int(mC.group(1)); mm = int(mC.group(2) or 0)
            t = _parse_24h(hh, mm)
            after_dt = now.replace(hour=t.hour, minute=t.minute, second=0, microsecond=0)
            return {"mode": "after_time", "after": after_dt, "duration_min": dur}

    # -------- Any slot this/next <weekday> (daypart)? [for <dur> min] --------
    m = re.search(
        r"\bany\s+slot\s+(this|next)\s+(mon|tue|wed|thu|thur|thurs|fri|sat|sun)"
        r"(?:\s+(morning|afternoon|evening))?(?:\s+for\s+(\d{1,3})\s*(?:min(?:ute)?s?|m))?",
        s
    )
    if m:
        this_next, wd, daypart, dur = m.group(1), m.group(2), m.group(3), m.group(4)
        target = now if this_next == "this" else now + timedelta(days=7)
        base = _next_weekday(target, _DAY_MAP[wd])
        duration = int(dur) if dur else 30
        if daypart:
            start_t, end_t = _daypart_bounds(daypart)
            day_start = base.replace(hour=start_t.hour, minute=start_t.minute, second=0, microsecond=0)
            day_end = base.replace(hour=end_t.hour, minute=end_t.minute, second=0, microsecond=0)
        else:
            day_start = base.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = base.replace(hour=23, minute=59, second=0, microsecond=0)
        return {"mode": "day_window", "start": day_start, "end": day_end, "duration_min": duration}

    # -------- Any slot (today|tomorrow) (daypart)? [for <dur> min] --------
    m = re.search(
        r"\bany\s+slot\s+(today|tomorrow)(?:\s+(morning|afternoon|evening))?(?:\s+for\s+(\d{1,3})\s*(?:min(?:ute)?s?|m))?",
        s
    )
    if m:
        day_word, daypart, dur = m.group(1), m.group(2), m.group(3)
        base = now if day_word == "today" else now + timedelta(days=1)
        duration = int(dur) if dur else 30
        if daypart:
            t1, t2 = _daypart_bounds(daypart)
            start = base.replace(hour=t1.hour, minute=t1.minute, second=0, microsecond=0)
            end = base.replace(hour=t2.hour, minute=t2.minute, second=0, microsecond=0)
        else:
            start = base.replace(hour=9, minute=0, second=0, microsecond=0)
            end = base.replace(hour=18, minute=0, second=0, microsecond=0)
        return {"mode": "day_window", "start": start, "end": end, "duration_min": duration}

    return None
