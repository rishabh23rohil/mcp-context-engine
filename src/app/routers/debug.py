from __future__ import annotations
from fastapi import APIRouter, Query
from ..core.config import settings
from ..providers.calendar_ics import CalendarICSProvider
from ..providers.calendar import CalendarProvider
from ..providers.notion import NotionProvider
from ..providers.github import GitHubProvider
import httpx
from icalendar import Calendar

router = APIRouter()  # prefix applied in main.py

def _calendar_provider():
    return CalendarICSProvider() if settings.CALENDAR_ICS_URL else CalendarProvider()

@router.get("/providers", tags=["debug"])
def providers():
    return {
        "calendar": type(_calendar_provider()).__name__,
        "notion": NotionProvider.__name__,
        "github": GitHubProvider.__name__,
    }

@router.get("/settings", tags=["debug"])
def redacted_settings():
    return {
        "APP_ENV": settings.APP_ENV,
        "CALENDAR_ICS_URL_set": bool(settings.CALENDAR_ICS_URL),
        "GITHUB_TOKEN_set": bool(settings.GITHUB_TOKEN),
        "NOTION_TOKEN_set": bool(settings.NOTION_TOKEN),
        "OPENAI_API_KEY_set": bool(settings.OPENAI_API_KEY),
    }

@router.get("/calendar", tags=["debug"])
async def calendar_preview(limit: int = Query(10, ge=1, le=50)):
    provider = _calendar_provider()
    items = await provider.fetch("debug", limit=limit)
    return {"provider": type(provider).__name__, "count": len(items), "items": items}

@router.get("/calendar/diag", tags=["debug"])
async def calendar_diag():
    """
    Deep-dive diagnostics for the ICS fetch/parse path.
    """
    if not settings.CALENDAR_ICS_URL:
        return {"ok": False, "why": "CALENDAR_ICS_URL is not set in .env"}

    # 1) Fetch
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(settings.CALENDAR_ICS_URL)
        fetch = {
            "ok": resp.is_success,
            "status": resp.status_code,
            "url": str(resp.url),
            "headers_sample": {k: resp.headers.get(k) for k in ["content-type", "content-length", "etag", "last-modified"]},
            "first_300_chars": resp.text[:300] if resp.text else None,
        }
    except Exception as e:
        return {"ok": False, "stage": "fetch", "error": str(e)}

    # 2) Parse
    try:
        cal = Calendar.from_ical(resp.content)
        vevents = [c for c in cal.walk("VEVENT")]
        # peek at first event fields
        peek = None
        if vevents:
            comp = vevents[0]
            peek = {
                "SUMMARY": str(comp.get("SUMMARY")),
                "DTSTART_raw": str(comp.get("DTSTART")),
                "DTEND_raw": str(comp.get("DTEND")),
            }
        return {"ok": True, "stage": "parse", "events_found": len(vevents), "fetch": fetch, "peek": peek}
    except Exception as e:
        return {"ok": False, "stage": "parse", "error": str(e), "fetch": fetch}
