from __future__ import annotations
from typing import List, Any
from fastapi import APIRouter
from ..schemas.query import QueryRequest, QueryResponse, ContextItem
from ..core.intent import classify_intent
from ..core.summarize import summarize
from ..core.config import settings
from ..providers.notion import NotionProvider
from ..providers.github import GitHubProvider
from ..providers.calendar import CalendarProvider
from ..providers.calendar_ics import CalendarICSProvider
from ..core.logging import get_logger

from ..core.availability import decide_availability, events_from_context_items

log = get_logger(__name__)
router = APIRouter(tags=["query"])

calendar_provider = CalendarICSProvider() if settings.CALENDAR_ICS_URL else CalendarProvider()
log.info(f"calendar.provider.selected provider={type(calendar_provider).__name__}")

PROVIDERS = {
    "calendar": calendar_provider,
    "notion": NotionProvider(),
    "github": GitHubProvider(),
}

def _select_sources(requested: List[str], intent: str) -> List[str]:
    if "all" in requested:
        order = [intent] + [s for s in ["calendar", "notion", "github"] if s != intent]
        return [s for s in order if s in PROVIDERS]
    return [s for s in requested if s in PROVIDERS]

@router.post("/query", response_model=QueryResponse)
async def handle_query(payload: QueryRequest) -> QueryResponse:
    intent = classify_intent(payload.query)
    selected = _select_sources(payload.sources, intent)

    raw_items: List[Any] = []
    for name in selected:
        provider = PROVIDERS.get(name)
        if not provider:
            continue
        items = await provider.fetch(payload.query, limit=5)
        raw_items.extend(items)

    # Normalize to ContextItem
    gathered: List[ContextItem] = []
    for it in raw_items:
        if isinstance(it, ContextItem):
            gathered.append(it)
        elif isinstance(it, dict):
            try:
                gathered.append(ContextItem(**it))
            except Exception as e:
                log.warning(f"normalize.context_item.failed error={e!r} it={it}")
        else:
            try:
                gathered.append(
                    ContextItem(
                        source=getattr(it, "source", "calendar"),
                        title=getattr(it, "title", "item"),
                        snippet=getattr(it, "snippet", ""),
                        url=getattr(it, "url", None),
                        metadata=getattr(it, "metadata", None),
                    )
                )
            except Exception as e:
                log.warning(f"normalize.context_item.unknown_type error={e!r} type={type(it)}")

    pkg = summarize(gathered, payload.max_tokens)

    availability = None
    conflicts = None
    explanation = None
    suggested_slots = None

    try:
        cal_events = events_from_context_items(gathered)
        result = decide_availability(query_text=payload.query, events=cal_events, cfg=settings)
        availability = result.availability
        conflicts = result.conflicts or None
        explanation = result.explanation or None
        suggested_slots = result.suggested_slots or None
    except Exception as e:
        log.warning(f"availability.compute.failed error={e!r}")


    return QueryResponse(
        intent=intent,
        context_items=gathered,
        context_package=pkg,
        availability=availability,
        conflicts=conflicts,
        explanation=explanation,
        suggested_slots=suggested_slots,
    )
