from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Sequence, TypedDict, Any, Tuple
from zoneinfo import ZoneInfo

from .timeparse import parse_query_to_windows, parse_slot_intent
from .config import settings
from .logging import get_logger
log = get_logger(__name__)


class _EventDict(TypedDict, total=False):
    title: str
    start: str
    end: str
    all_day: bool


@dataclass
class BusyBlock:
    title: str
    start: datetime
    end: datetime
    all_day: bool = False


@dataclass
class AvailabilityResult:
    availability: str          # "free" | "busy" | "unknown"
    conflicts: List[dict]
    explanation: str
    suggested_slots: List[dict]   # may be []


def _parse_iso(dt_str: str, tz: ZoneInfo) -> datetime:
    dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=tz)
    return dt.astimezone(tz)


def _overlap(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool:
    if getattr(settings, "AVAILABILITY_EDGE_POLICY", "exclusive_end") == "inclusive":
        return a_start <= b_end and b_start <= a_end
    return (a_start < b_end) and (b_start < a_end)


def events_from_context_items(items: Sequence[Any]) -> List[_EventDict]:
    out: List[_EventDict] = []
    for it in items:
        if isinstance(it, dict):
            if it.get("source") != "calendar":
                continue
            md = it.get("metadata") or {}
            if "start" in md and "end" in md:
                out.append({
                    "title": md.get("title") or it.get("title", "calendar event"),
                    "start": md["start"],
                    "end": md["end"],
                    "all_day": bool(md.get("all_day", False)),
                })
            continue

        if getattr(it, "source", None) != "calendar":
            continue
        md = getattr(it, "metadata", None) or {}
        if "start" in md and "end" in md:
            out.append({
                "title": md.get("title") or getattr(it, "title", "calendar event"),
                "start": md["start"],
                "end": md["end"],
                "all_day": bool(md.get("all_day", False)),
            })
    return out


def _merge_overlaps(blocks: List[BusyBlock]) -> List[BusyBlock]:
    if not blocks:
        return []
    blocks = sorted(blocks, key=lambda b: (b.start, b.end))
    merged: List[BusyBlock] = [blocks[0]]
    for b in blocks[1:]:
        last = merged[-1]
        if _overlap(last.start, last.end, b.start, b.end) or last.end == b.start:
            if b.end > last.end:
                last.end = b.end
        else:
            merged.append(b)
    return merged


def _work_window_for(day: datetime, cfg) -> Tuple[datetime, datetime]:
    sh, sm = map(int, getattr(cfg, "WORK_HOURS_START", "09:00").split(":"))
    eh, em = map(int, getattr(cfg, "WORK_HOURS_END", "18:00").split(":"))
    start = day.replace(hour=sh, minute=sm, second=0, microsecond=0)
    end = day.replace(hour=eh, minute=em, second=0, microsecond=0)
    return start, end


def _suggest_slots_in_window(
    blocks: List[BusyBlock],
    win_start: datetime,
    win_end: datetime,
    duration_min: int,
    max_suggestions: int = 2,
) -> List[dict]:
    """Return earliest free slots (start,end) within [win_start, win_end)."""
    suggestions: List[dict] = []
    cursor = win_start

    for b in blocks:
        # skip blocks fully outside window
        if b.end <= win_start or b.start >= win_end:
            continue

        # free segment from cursor to the start of this busy block
        if cursor < b.start:
            seg_end = min(b.start, win_end)
            if seg_end - cursor >= timedelta(minutes=duration_min):
                suggestions.append({
                    "start": cursor.isoformat(),
                    "end": (cursor + timedelta(minutes=duration_min)).isoformat(),
                    "reason": "earliest free segment",
                })
                if len(suggestions) >= max_suggestions:
                    return suggestions

        # advance cursor past this busy block
        cursor = max(cursor, b.end)
        if cursor >= win_end:
            break

    # tail segment after the last busy block
    if cursor < win_end and (win_end - cursor) >= timedelta(minutes=duration_min):
        suggestions.append({
            "start": cursor.isoformat(),
            "end": (cursor + timedelta(minutes=duration_min)).isoformat(),
            "reason": "earliest free segment",
        })

    return suggestions


def suggest_slots(query_text: str, events: List[_EventDict], cfg, max_suggestions: int = 2) -> List[dict]:
    """Parses slot intent and returns suggested free slots or []."""
    # tz (Windows-safe)
    try:
        tz = ZoneInfo(cfg.DEFAULT_TZ)
    except Exception:
        from dateutil.tz import tzlocal
        tz = tzlocal()

    intent = parse_slot_intent(query_text, tz=tz)
    if not intent:
        return []

    # normalize events
    blocks: List[BusyBlock] = []
    for ev in events:
        try:
            s = _parse_iso(ev["start"], tz)
            e = _parse_iso(ev["end"], tz)
            blocks.append(BusyBlock(
                title=ev.get("title", "event"),
                start=s, end=e,
                all_day=bool(ev.get("all_day", False)),
            ))
        except Exception:
            continue

    # expand all-day to full-day blocks
    expanded: List[BusyBlock] = []
    for b in blocks:
        if b.all_day:
            d0 = b.start.replace(hour=0, minute=0, second=0, microsecond=0)
            expanded.append(BusyBlock(b.title, d0, d0 + timedelta(days=1), all_day=True))
        else:
            expanded.append(b)
    blocks = _merge_overlaps(expanded)

    if intent["mode"] == "after_time":
        after: datetime = intent["after"]
        dur = intent["duration_min"]
        day_start, day_end = _work_window_for(after, cfg)
        win_start = max(after, day_start)
        win_end = day_end
        return _suggest_slots_in_window(blocks, win_start, win_end, dur, max_suggestions)

    if intent["mode"] == "day_window":
        start: datetime = intent["start"]
        end: datetime = intent["end"]
        dur = intent["duration_min"]
        ws, we = _work_window_for(start, cfg)
        win_start = max(start, ws)
        win_end = min(end, we)
        if win_end <= win_start:
            return []
        return _suggest_slots_in_window(blocks, win_start, win_end, dur, max_suggestions)

    return []


def decide_availability(query_text: str, events: List[_EventDict], cfg) -> AvailabilityResult:
    """
    - Parses a free/busy window from the query (24h clock + dayparts + next <wd>).
    - Computes conflicts against calendar events (incl. all-day & edge policy).
    - When RANGE queries conflict, suggests earliest in-window slots honoring requested duration.
    - When RANGE queries are free and a duration was requested, suggests earliest slots in window.
    - If no window was parsed, treats it as a slot-finding query via parse_slot_intent().
    """
    # --- timezone (Windows-safe) ---
    try:
        tz = ZoneInfo(cfg.DEFAULT_TZ)
    except Exception:
        from dateutil.tz import tzlocal
        tz = tzlocal()

    # --- try direct free/busy window first ---
    windows = parse_query_to_windows(query_text, tz=tz)

    # Normalize calendar events → BusyBlock[]
    blocks: List[BusyBlock] = []
    for ev in events:
        try:
            s = _parse_iso(ev["start"], tz)
            e = _parse_iso(ev["end"], tz)
            blocks.append(
                BusyBlock(
                    title=ev.get("title", "event"),
                    start=s,
                    end=e,
                    all_day=bool(ev.get("all_day", False)),
                )
            )
        except Exception:
            continue

    # Helper to expand all-day blocks to civil-day spans for slot math
    def _expand_all_day(bs: List[BusyBlock]) -> List[BusyBlock]:
        out: List[BusyBlock] = []
        for b in bs:
            if b.all_day:
                d0 = b.start.replace(hour=0, minute=0, second=0, microsecond=0)
                out.append(BusyBlock(b.title, d0, d0 + timedelta(days=1), all_day=True))
            else:
                out.append(b)
        return out

    blocks_for_slots = _merge_overlaps(_expand_all_day(blocks))

    # If no explicit free/busy window parsed, try pure slot intent (e.g., "book 30 min after 15:00 today")
    if not windows:
        suggestions = suggest_slots(query_text, events, cfg)
        if suggestions:
            return AvailabilityResult("unknown", [], "Suggested slots available.", suggestions)
        return AvailabilityResult("unknown", [], "Could not resolve a specific time window.", [])

    # We have a window
    w_start, w_end = windows[0]
    point_mode = (w_start == w_end)

    # --- conflict detection (handles all-day distinctly) ---
    conflicting: List[BusyBlock] = []
    for b in blocks:
        if b.all_day:
            day_start = b.start.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            if point_mode:
                if day_start <= w_start < day_end:
                    conflicting.append(b)
            else:
                if _overlap(w_start, w_end, day_start, day_end):
                    conflicting.append(b)
        else:
            if point_mode:
                if b.start <= w_start < b.end:
                    conflicting.append(b)
            else:
                if _overlap(w_start, w_end, b.start, b.end):
                    conflicting.append(b)

    if conflicting:
        # shape conflicts
        conflicts_out = [
            {
                "title": c.title,
                "start": c.start.isoformat(),
                "end": c.end.isoformat(),
                "all_day": c.all_day,
                "source": "calendar",
            }
            for c in sorted(conflicting, key=lambda x: (x.start, x.end))
        ]

        if point_mode:
            return AvailabilityResult(
                "busy",
                conflicts_out,
                f"Conflicts with {conflicts_out[0]['title']} at {conflicts_out[0]['start'][11:16]}.",
                []
            )

        # RANGE conflict: suggest earliest in-window slots honoring requested duration (default 30)
        slot_intent = parse_slot_intent(query_text, tz=tz)
        requested_dur = 30
        if slot_intent and slot_intent.get("mode") == "day_window":
            requested_dur = int(slot_intent.get("duration_min", 30))

        suggestions_in_window = _suggest_slots_in_window(
            blocks_for_slots,            # merged & all-day-expanded
            w_start,
            w_end,
            duration_min=requested_dur,
            max_suggestions=2,
        )

        return AvailabilityResult(
            "busy",
            conflicts_out,
            f"Conflicts with {conflicts_out[0]['title']} "
            f"{conflicts_out[0]['start'][11:16]}–{conflicts_out[0]['end'][11:16]}.",
            suggestions_in_window,
        )

    # No conflicts → free. If the user asked for a duration in a RANGE, propose earliest slots in window.
    slot_intent = parse_slot_intent(query_text, tz=tz)
    if slot_intent and slot_intent.get("mode") == "day_window":
        dur = int(slot_intent.get("duration_min", 30))
        suggestions_if_free = _suggest_slots_in_window(
            blocks_for_slots,
            w_start,
            w_end,
            duration_min=dur,
            max_suggestions=2,
        )
        if suggestions_if_free:
            return AvailabilityResult(
                "free",
                [],
                "Window is free; suggested earliest slots.",
                suggestions_if_free,
            )

    return AvailabilityResult("free", [], "No conflicts in the requested window.", [])
