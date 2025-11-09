# src/app/core/nlp.py
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict

CALENDAR_KWS = {"free", "busy", "meeting", "schedule", "calendar", "tomorrow", "today", "slot"}
NOTION_KWS   = {"notes", "meeting notes", "decisions", "retro", "action items", "doc", "wiki", "page"}
GITHUB_KWS   = {"issue", "issues", "pr", "pull", "pipeline", "deploy", "status", "prod", "bug", "cpu"}

@dataclass
class Intent:
    name: str
    sources: List[str]

def detect_intent(q: str) -> Intent:
    text = (q or "").lower()

    score = {"calendar": 0, "notion": 0, "github": 0}
    score["calendar"] += sum(k in text for k in CALENDAR_KWS)
    score["notion"]   += sum(k in text for k in NOTION_KWS)
    score["github"]   += sum(k in text for k in GITHUB_KWS)

    if max(score.values()) == 0:
        return Intent(name="general", sources=["calendar", "notion", "github"])

    ordered = sorted(score.items(), key=lambda kv: kv[1], reverse=True)
    top = [s for s, v in ordered if v == ordered[0][1]]
    return Intent(name=top[0], sources=top)

def summarize_items(items: List[Dict], max_items: int = 5) -> Dict:
    # Small “signal, not noise” packer.
    items = items[:max_items]
    highlights = [i.get("title") or i.get("snippet") for i in items if i]
    return {
        "tokens": sum(len((i.get("snippet") or "")) // 4 + 10 for i in items),
        "summary": " - " + " | ".join((h or "") for h in highlights if h),
        "highlights": highlights[:3],
    }
