from __future__ import annotations
from typing import List, Any, Dict, Optional
import httpx
from ..schemas.query import ContextItem
from ..core.config import settings
from ..core.logging import get_logger

log = get_logger(__name__)

NOTION_API = "https://api.notion.com/v1/search"
NOTION_VERSION = "2022-06-28"  # stable, works fine for simple search


def _first_title_from_properties(props: Dict[str, Any]) -> Optional[str]:
    # Try common title-ish fields
    # Priority: 'Name' (common in DBs), then any property with type 'title'
    if not isinstance(props, dict):
        return None
    if "Name" in props and props["Name"].get("type") == "title":
        arr = props["Name"].get("title") or []
        if arr and isinstance(arr, list) and "plain_text" in arr[0]:
            return arr[0]["plain_text"] or None
    # Fallback: find first title property
    for k, v in props.items():
        if isinstance(v, dict) and v.get("type") == "title":
            arr = v.get("title") or []
            if arr and isinstance(arr, list) and "plain_text" in arr[0]:
                return arr[0]["plain_text"] or None
    return None


class NotionProvider:
    name = "notion"

    async def fetch(self, query: str, limit: int = 5) -> List[ContextItem]:
        token = settings.NOTION_TOKEN
        if not token:
            # Graceful stub when token not present
            return [
                ContextItem(
                    source="notion",
                    title="(notion) token not configured",
                    snippet="Set NOTION_TOKEN in .env to enable live search.",
                    url=None,
                    metadata={"query": query},
                )
            ][: min(limit, 1)]

        headers = {
            "Authorization": f"Bearer {token}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json",
        }
        body = {
            "query": query or "",  # Notion requires a string
            "sort": {"direction": "descending", "timestamp": "last_edited_time"},
            # We don’t require a filter here; this returns pages and databases.
        }

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(NOTION_API, headers=headers, json=body)
                resp.raise_for_status()
                data = resp.json()
        except Exception as e:
            log.warning("notion.fetch.failed error=%r", e)
            return [
                ContextItem(
                    source="notion",
                    title="(notion) fetch error",
                    snippet=str(e),
                    url=None,
                    metadata={"query": query},
                )
            ][:1]

        results = data.get("results", []) or []
        items: List[ContextItem] = []
        for r in results:
            if r.get("object") not in {"page", "database"}:
                continue
            url = r.get("url")
            props = r.get("properties", {}) if r.get("object") == "page" else {}
            title = _first_title_from_properties(props) or r.get("title") or "Notion item"
            snippet = "Notion page" if r.get("object") == "page" else "Notion database"
            items.append(
                ContextItem(
                    source="notion",
                    title=str(title),
                    snippet=snippet,
                    url=url,
                    metadata={
                        "object": r.get("object"),
                        "last_edited_time": r.get("last_edited_time"),
                    },
                )
            )
            if len(items) >= limit:
                break

        if not items:
            items.append(
                ContextItem(
                    source="notion",
                    title="(notion) no results",
                    snippet="No matching pages/databases.",
                    url=None,
                    metadata={"query": query},
                )
            )
        return items
