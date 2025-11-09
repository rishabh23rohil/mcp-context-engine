from __future__ import annotations
from typing import List
from ..schemas.query import ContextItem


class GitHubProvider:
    name = "github"

    async def fetch(self, query: str, limit: int = 5) -> List[ContextItem]:
        # Stubbed data; replace with real GitHub API later
        items: List[ContextItem] = [
            ContextItem(
                source="github",
                title="prod-web status",
                snippet="3 instances healthy; web-01 CPU ~85%, others ~30%.",
                url="https://github.com/your/repo/issues/123",
                metadata={"severity": "warning"},
            ),
            ContextItem(
                source="github",
                title="Open PR: hotfix reduce CPU",
                snippet="Reduces polling interval; adds backoff.",
                url="https://github.com/your/repo/pull/456",
                metadata={"labels": ["hotfix", "infra"]},
            ),
        ]
        return items[:limit]
