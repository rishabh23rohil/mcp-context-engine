from __future__ import annotations
from typing import List
import httpx
from ..schemas.query import ContextItem
from ..core.config import settings
from ..core.logging import get_logger

log = get_logger(__name__)
GITHUB_SEARCH = "https://api.github.com/search/issues"


class GitHubProvider:
    name = "github"

    async def fetch(self, query: str, limit: int = 5) -> List[ContextItem]:
        token = settings.GITHUB_TOKEN
        if not token:
            return [
                ContextItem(
                    source="github",
                    title="(github) token not configured",
                    snippet="Set GITHUB_TOKEN in .env to enable live search.",
                    url=None,
                    metadata={"query": query},
                )
            ][: min(limit, 1)]

        # Build a broad query: open issues/PRs, sorted by recency
        # You can refine by labels or repo in the user query itself.
        q = (query or "").strip()
        if not q:
            q = "is:open"  # generic

        params = {
            "q": f"{q} is:open",
            "sort": "updated",
            "order": "desc",
            "per_page": str(min(limit, 5)),
        }
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        }

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(GITHUB_SEARCH, headers=headers, params=params)
                resp.raise_for_status()
                data = resp.json()
        except Exception as e:
            log.warning("github.fetch.failed error=%r", e)
            return [
                ContextItem(
                    source="github",
                    title="(github) fetch error",
                    snippet=str(e),
                    url=None,
                    metadata={"query": query},
                )
            ][:1]

        items: List[ContextItem] = []
        for n in (data.get("items") or []):
            title = n.get("title") or "GitHub item"
            html_url = n.get("html_url")
            # Build a short snippet
            state = n.get("state")
            is_pr = "pull_request" in n
            who = (n.get("user") or {}).get("login")
            snippet = f"{'PR' if is_pr else 'Issue'} • {state} • by {who}"
            items.append(
                ContextItem(
                    source="github",
                    title=title,
                    snippet=snippet,
                    url=html_url,
                    metadata={
                        "is_pr": bool(is_pr),
                        "repo": (n.get("repository_url") or "").rsplit("/", 1)[-1],
                        "updated_at": n.get("updated_at"),
                        "labels": [l.get("name") for l in (n.get("labels") or []) if isinstance(l, dict)],
                    },
                )
            )
            if len(items) >= limit:
                break

        if not items:
            items.append(
                ContextItem(
                    source="github",
                    title="(github) no results",
                    snippet="No open issues/PRs matched.",
                    url=None,
                    metadata={"query": query},
                )
            )
        return items
