```markdown
# MCP Context Engine

A minimal **context-aware middleware** (MCP-style) that fetches real-world data and returns AI-ready context.

**Milestones complete**
- **M0** – FastAPI scaffold, config, logging, error handling  
- **M1** – Health & diagnostics routes  
- **M2** – Google Calendar (ICS) provider with diagnostics & event listing  
- **M3** – Natural-language availability + slot suggestion engine ✅

---
## Screenshots

> Taken from **Swagger → POST /query** using your live calendar ICS.

### 🧭 Swagger Home
Displays the interactive API interface for querying your calendar context.

![Swagger Home](https://github.com/rishabh23rohil/mcp-context-engine/blob/main/screenshots/swagger-home.png?raw=true)

---

### 📅 Busy Check
Example query: `am I free tomorrow at 03:10?`  
Shows the model determining whether the user is busy at a given time.

![Calendar Busy](https://github.com/rishabh23rohil/mcp-context-engine/blob/main/screenshots/calendar-busy.png?raw=true)

---

### ⏰ Slot Suggestion
Example query: `any slot tomorrow morning for 45 min`  
Shows the system suggesting the next available free slot.

![Calendar Slot](https://github.com/rishabh23rohil/mcp-context-engine/blob/main/screenshots/calendar-slot.png?raw=true)


---

## Stack
- Python 3.11+ (works on 3.13)
- FastAPI + Uvicorn
- httpx, icalendar
- pydantic-settings for `.env`
- tzdata / dateutil for safe timezones

---

## Repo layout (key)

```

src/
app/
core/              # config, logging, availability, nlp, timeparse
providers/         # calendar_ics.py (M2), calendar.py (fallback)
routers/           # query.py, debug.py (diagnostics)
main.py            # FastAPI entrypoint
.env.example
requirements.txt
tests/
screenshots/          # images referenced in this README

````

---

## Prerequisites
- Python **3.11+**
- Git
- A Google Calendar you can access (ICS URL)

---

## Setup (local)

> PowerShell (Windows) shown. macOS/Linux: `source .venv/bin/activate`.

### 1) Create & activate venv
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
````

### 2) Install deps

```powershell
pip install -r requirements.txt
```

### 3) Copy env template

```powershell
Copy-Item .env.example .env
```

### 4) Get your **Secret iCal** URL

Google Calendar → **Settings** → your calendar → **Integrate calendar** → **Secret address in iCal format**
Looks like:

```
https://calendar.google.com/calendar/ical/<your-id>/private-<long-token>/basic.ics
```

> Avoid the public link unless you’ve made the calendar public (otherwise you’ll get HTML/404).

### 5) Fill `.env`

```
APP_ENV=local
DEFAULT_TZ=America/Chicago
WORK_HOURS_START=09:00
WORK_HOURS_END=18:00
AVAILABILITY_EDGE_POLICY=exclusive_end

# Providers
CALENDAR_ICS_URL=YOUR_SECRET_ICS_URL_HERE
GITHUB_TOKEN=          # optional (M4+)
NOTION_TOKEN=          # optional (M4+)
```

---

## Run

```powershell
python -m uvicorn src.app.main:app --reload --port 8000
```

Open Swagger: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## Quick checks

| Endpoint                      | Purpose                                                 |
| ----------------------------- | ------------------------------------------------------- |
| `GET /healthz`                | Liveness                                                |
| `GET /version`                | Build tag                                               |
| `GET /debug/providers`        | Confirms calendar provider                              |
| `GET /debug/settings`         | Shows redacted env snapshot                             |
| `GET /debug/calendar?limit=5` | Lists upcoming events                                   |
| `GET /debug/calendar/diag`    | Fetch/parse diagnostics (great for ICS issues)          |
| **`POST /query`**             | Main context engine (intent + providers + availability) |

---

## Example queries (24-hour clock)

| Query                                    | Expect                                                                |
| ---------------------------------------- | --------------------------------------------------------------------- |
| `am I free tomorrow at 03:10?`           | **busy** if you have a 03–04 event                                    |
| `am I free tomorrow at 11:30?`           | **free**                                                              |
| `any slot tomorrow morning for 45 min`   | **busy/free**, with **suggested_slots** if applicable                 |
| `any slot tomorrow afternoon for 30 min` | **free** with **suggested_slots**                                     |
| `book 30 min after 15:00 today`          | **unknown** (not a direct window), **suggested_slots** at/after 15:00 |

---

## Response shapes (high level)

**Busy (point)**

```json
{
  "availability": "busy",
  "conflicts": [
    {"title":"testing","start":"...03:00...","end":"...04:00...","all_day":false}
  ],
  "explanation": "Conflicts with testing at 03:00."
}
```

**Busy (range) with suggestions**

```json
{
  "availability": "busy",
  "explanation": "Conflicts with test1 09:00–10:00.",
  "suggested_slots": [
    {"start":"2025-11-10T10:00:00-06:00","end":"2025-11-10T10:45:00-06:00","reason":"earliest free segment"}
  ]
}
```

**Unknown + suggestions (slot phrasing)**

```json
{
  "availability": "unknown",
  "explanation": "Suggested slots available.",
  "suggested_slots": [
    {"start":"2025-11-08T15:00:00-06:00","end":"2025-11-08T15:30:00-06:00","reason":"earliest free segment"}
  ]
}
```

---

## Testing

```bash
pytest tests -q
```

Covers:

* 24h parsing & dayparts (morning/afternoon/evening)
* Inclusive/exclusive edge rules
* All-day/multi-day normalization
* “after 15:00 today” slot generation
* Day-window suggestions within work hours

---

## Troubleshooting

**ICS returns HTML/404**
Use the **Secret address in iCal format**, not the public one (unless calendar is public).

**Wrong timezone**
Adjust in Google Calendar (General → Time Zone). We output local-time snippets and ISO timestamps with offsets.

**Diagnostics**
Call `/debug/calendar/diag` → the `"stage"` and `"fetch"` sections will tell you exactly what failed (DNS, 404, parse, etc.).

---

## Roadmap / What’s next

* **M4 (optional)**: Live GitHub search (issues/PRs) using `GITHUB_TOKEN`.
  Example test (Swagger → POST /query):

  ```json
  { "query": "list open issues created by rishabh23rohil", "sources": ["github"], "max_tokens": 256 }
  ```


---

## Requirements (pinned)

> Keep these in `requirements.txt` to reproduce your environment.

```
fastapi>=0.115.0
uvicorn[standard]>=0.30.0
pydantic>=2.7.0
pydantic-settings>=2.3.0
httpx>=0.27.0
icalendar>=5.0.12
python-dateutil>=2.9.0.post0
tzdata>=2024.1
```





