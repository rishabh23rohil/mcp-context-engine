from __future__ import annotations
from typing import List
from fastapi import APIRouter
from ..schemas.query import QueryRequest, QueryResponse, ContextItem
from ..core.intent import classify_intent
from ..core.summarize import summarize
from ..core.config import settings
from ..providers.notion import NotionProvider
from ..providers.github import GitHubProvider
from ..providers.calendar import CalendarProvider
from ..providers.calendar_ics import CalendarICSProvider  # <-- NEW
from ..core.logging import get_logger
log = get_logger(__name__)

calendar_provider = CalendarICSProvider() if settings.CALENDAR_ICS_URL else CalendarProvider()
log.info(f"calendar.provider.selected provider={type(calendar_provider).__name__}")



router = APIRouter(tags=["query"])

# Provider registry (ICS if configured, else stub calendar)
calendar_provider = CalendarICSProvider() if settings.CALENDAR_ICS_URL else CalendarProvider()

PROVIDERS = {
    "calendar": calendar_provider,
    "notion": NotionProvider(),
    "github": GitHubProvider(),
}

def _select_sources(requested: List[str], intent: str) -> List[str]:
    if "all" in requested:
        order = [intent] + [s for s in ["calendar", "notion", "github"] if s != intent]
        return order
    return [s for s in requested if s in PROVIDERS]

@router.post("/query", response_model=QueryResponse)
async def handle_query(payload: QueryRequest) -> QueryResponse:
    intent = classify_intent(payload.query)
    selected = _select_sources(payload.sources, intent)

    gathered: List[ContextItem] = []
    for name in selected:
        provider = PROVIDERS.get(name)
        if not provider:
            continue
        items = await provider.fetch(payload.query, limit=5)
        gathered.extend(items)

    pkg = summarize(gathered, payload.max_tokens)
    return QueryResponse(intent=intent, context_items=gathered, context_package=pkg)
