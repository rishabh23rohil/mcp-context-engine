from __future__ import annotations
from typing import Any, Literal, List, Optional
from pydantic import BaseModel, Field


SourceName = Literal["calendar", "notion", "github", "all"]


class QueryRequest(BaseModel):
    query: str = Field(..., description="User's natural language query")
    sources: List[SourceName] = Field(
        default_factory=lambda: ["all"],
        description='Preferred sources: "calendar" | "notion" | "github" | "all"',
    )
    max_tokens: int = Field(512, ge=64, le=4096)


class ContextItem(BaseModel):
    source: SourceName
    title: str
    snippet: str
    url: Optional[str] = None
    metadata: dict[str, Any] | None = None


class ContextPackage(BaseModel):
    tokens: int
    summary: str
    highlights: List[str] = Field(default_factory=list)


class QueryResponse(BaseModel):
    intent: Literal["calendar", "code", "notes", "general"]
    context_items: List[ContextItem]
    context_package: ContextPackage
