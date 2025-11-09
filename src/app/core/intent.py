from __future__ import annotations

def classify_intent(text: str) -> str:
    s = (text or "").lower()

    # Calendar-like keywords (free/busy, slots, booking)
    cal_terms = (
        "am i free",
        "free at", "busy at",
        "tomorrow", "today", "next ",
        "slot", "book", "schedule", "reschedule",
        "morning", "afternoon", "evening",
    )
    if any(t in s for t in cal_terms):
        return "calendar"

    # Light heuristics for others
    if "notion" in s or "notes" in s or "meeting notes" in s:
        return "notes"
    if "github" in s or "pr " in s or "issue " in s:
        return "code"

    return "general"
