from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
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
    if hasattr(value, "dt"):
        value = value.dt

    if isinstance(value, datetime):
        dt = value
    else:
        # date -> datetime at 00:00
        try:
            from datetime import date as _date

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
            start = _to_dt(comp.get("DTSTART"))
            end = _to_dt(comp.get("DTEND"))

            if not summary or not start:
                continue

            # Only upcoming-ish events
            if end and end < now:
                continue
            if start > horizon:
                continue

            # Optional dumb text filter with the user query
            if query and query.strip():
                q = query.lower()
                if q not in str(summary).lower():
                    # you can enrich here (location/description) if needed
                    pass

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
                    },
                }
            )

        # sort and cap
        items.sort(key=lambda x: x["metadata"]["start"])
        return items[:limit]
