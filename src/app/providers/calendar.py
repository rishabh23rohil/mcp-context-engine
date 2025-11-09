from __future__ import annotations
from typing import List
from datetime import datetime, timedelta
from ..schemas.query import ContextItem


class CalendarProvider:
    name = "calendar"

    async def fetch(self, query: str, limit: int = 5) -> List[ContextItem]:
        # Very light heuristic to fabricate an event based on "tomorrow at 10"
        now = datetime.now()
        if "tomorrow" in query.lower():
            day = now + timedelta(days=1)
        else:
            day = now
        start = day.replace(hour=10, minute=0, second=0, microsecond=0)
        end = start + timedelta(hours=1)

        items: List[ContextItem] = [
            ContextItem(
                source="calendar",
                title="Project Sync",
                snippet=f"{start.strftime('%Y-%m-%d %H:%M')} - {end.strftime('%H:%M')} (local time)",
                url=None,
                metadata={"start": start.isoformat(), "end": end.isoformat()},
            ),
        ]
        return items[:limit]
