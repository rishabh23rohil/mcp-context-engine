from __future__ import annotations
from typing import List
from ..schemas.query import ContextItem, ContextPackage


def _count_tokens(text: str) -> int:
    # naive token estimator (whitespace split)
    return max(1, len(text.split()))


def summarize(items: List[ContextItem], max_tokens: int) -> ContextPackage:
    if not items:
        return ContextPackage(tokens=0, summary="No context found.", highlights=[])

    # Build a very short, dense summary
    lines = [f"- [{it.source}] {it.title}: {it.snippet}" for it in items[:6]]
    raw = "\n".join(lines)
    # Truncate roughly to max_tokens by words
    words = raw.split()
    if len(words) > max_tokens:
        words = words[:max_tokens - 3] + ["..."]
    summary = " ".join(words)

    # simple highlights
    highlights = [it.title for it in items[:3]]

    return ContextPackage(tokens=_count_tokens(summary), summary=summary, highlights=highlights)
