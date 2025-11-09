from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone, date as _date
from typing import Any, List, Dict

import httpx
from icalendar import Calendar
from dateutil.tz import tzlocal

from ..core.config import settings

LOCAL_TZ = tzlocal()


def _to_dt(value: Any) -> datetime | None:
    """
    icalendar can yield date or datetime, tz-aware or naive.
    Normalize to local tz-aware datetime.
    """
    if value is None:
        return None

    # VEVENT fields are often wrapped objects exposing .dt
    raw = value
    if hasattr(value, "dt"):
        value = value.dt

    if isinstance(value, datetime):
        dt = value
    else:
        # date -> datetime at 00:00
        try:
            if isinstance(value, _date):
                dt = datetime(value.year, value.month, value.day)
            else:
                return None
        except Exception:
            return None

    # attach timezone if missing
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    # convert to local tz
    return dt.astimezone(LOCAL_TZ)


def _is_all_day(dt_prop: Any) -> bool:
    """
    Heuristic:
    - VALUE=DATE or .dt is a date (not datetime) => all-day.
    """
    try:
        # icalendar.vDDDTypes keeps params
        if hasattr(dt_prop, "params") and dt_prop.params.get("VALUE", "").upper() == "DATE":
            return True
        if hasattr(dt_prop, "dt"):
            val = dt_prop.dt
            return isinstance(val, _date) and not isinstance(val, datetime)
    except Exception:
        pass
    return False


class CalendarICSProvider:
    """
    Pulls upcoming events from a Google Calendar ICS URL and emits context items.
    """

    def __init__(self, timeout_s: float = 10.0) -> None:
        if not settings.CALENDAR_ICS_URL:
            raise RuntimeError("CALENDAR_ICS_URL is not set")
        self.url = settings.CALENDAR_ICS_URL
        self.timeout_s = timeout_s

    async def fetch(self, query: str, *, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Return upcoming events (next 30 days) as context items.
        """
        async with httpx.AsyncClient(timeout=self.timeout_s) as client:
            resp = await client.get(self.url)
            resp.raise_for_status()
            ics_bytes = resp.content

        cal = Calendar.from_ical(ics_bytes)
        now = datetime.now(LOCAL_TZ)
        horizon = now + timedelta(days=30)

        items: List[Dict[str, Any]] = []
        for comp in cal.walk("VEVENT"):
            summary = comp.get("SUMMARY")
            dtstart_prop = comp.get("DTSTART")
            dtend_prop = comp.get("DTEND")

            start = _to_dt(dtstart_prop)
            end = _to_dt(dtend_prop) if dtend_prop else None
            if not summary or not start:
                continue

            # All-day detection
            all_day = _is_all_day(dtstart_prop)

            # If all-day and no explicit DTEND, treat as one full day
            if all_day and not end:
                end = (start + timedelta(days=1)).replace(microsecond=0)

            # Only upcoming-ish events
            if end and end < now:
                continue
            if start > horizon:
                continue

            # Optional light filter on summary (no-op for now)
            if query and query.strip():
                _ = query  # placeholder for future scoring

            snippet = (
                f"{start.strftime('%Y-%m-%d %H:%M')} - "
                f"{(end or start).strftime('%H:%M')} (local time)"
            )

            items.append(
                {
                    "source": "calendar",
                    "title": str(summary),
                    "snippet": snippet,
                    "url": None,
                    "metadata": {
                        "start": start.replace(microsecond=0).isoformat(),
                        "end": (end or start).replace(microsecond=0).isoformat(),
                        "all_day": bool(all_day),
                        "title": str(summary),
                    },
                }
            )

        # sort and cap
        items.sort(key=lambda x: x["metadata"]["start"])
        return items[:limit]
