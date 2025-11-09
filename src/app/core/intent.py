from __future__ import annotations


def classify_intent(query: str) -> str:
    q = query.lower()

    calendar_keys = ["free", "availability", "meeting", "schedule", "calendar", "tomorrow", "today", "am", "pm"]
    notes_keys = ["notes", "meeting notes", "decisions", "action items", "doc", "page", "notion", "minutes"]
    code_keys = ["repo", "pull request", "pr", "issue", "branch", "deploy", "ci", "build", "github"]

    if any(k in q for k in calendar_keys):
        return "calendar"
    if any(k in q for k in notes_keys):
        return "notes"
    if any(k in q for k in code_keys):
        return "code"
    return "general"
