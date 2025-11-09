from __future__ import annotations
from typing import List
from ..schemas.query import ContextItem


class NotionProvider:
    name = "notion"

    async def fetch(self, query: str, limit: int = 5) -> List[ContextItem]:
        # Stubbed data; replace with real Notion search later
        items: List[ContextItem] = [
            ContextItem(
                source="notion",
                title="Project Phoenix - Launch Meeting",
                snippet="Decisions: Q3 launch; Marketing to highlight speed.",
                url="https://notion.so/workspace/project-phoenix",
                metadata={"page": "Meeting Notes", "decision_count": 2},
            ),
            ContextItem(
                source="notion",
                title="Retro Actions - Phoenix",
                snippet="Action items: finalize rollout plan; prepare FAQ.",
                url="https://notion.so/workspace/retro-actions",
                metadata={"action_items": 2},
            ),
        ]
        return items[:limit]
