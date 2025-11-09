from __future__ import annotations
from typing import List
from fastapi import APIRouter
from ..schemas.query import QueryRequest, QueryResponse, ContextItem
from ..core.intent import classify_intent
from ..core.summarize import summarize
from ..providers.calendar import CalendarProvider
from ..providers.notion import NotionProvider
from ..providers.github import GitHubProvider

router = APIRouter(tags=["query"])

# Provider registry (stubbed)
PROVIDERS = {
    "calendar": CalendarProvider(),
    "notion": NotionProvider(),
    "github": GitHubProvider(),
}

def _select_sources(requested: List[str], intent: str) -> List[str]:
    if "all" in requested:
        # bias to intent first
        order = [intent] + [s for s in ["calendar", "notion", "github"] if s != intent]
        return order
    # keep order, but ensure only known providers
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
