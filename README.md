Here’s your **updated full README.md** for **Milestone 3**, continuing your previous structure and style, but upgraded for the new calendar reasoning + slot engine:

---

```markdown
# MCP Context Engine

A minimal **context-aware middleware** (MCP-style) that fetches real-world data and outputs AI-ready context.  

**Milestones complete:**  
- **M0** – FastAPI scaffold, config, logging, error handling  
- **M1** – Health & diagnostics routes  
- **M2** – Google Calendar (ICS) provider with diagnostics & event listing  
- **M3** – Natural-language availability + slot suggestion engine ✅  

---

## Stack
- Python 3.11 + (works on 3.13)
- FastAPI + Uvicorn
- httpx, icalendar
- pydantic-settings for `.env`

---

## Repo layout (key)

```

src/
app/
core/              # config, logging, error handling, availability, nlp, timeparse
providers/         # calendar_ics.py (M2), calendar.py (M3)
routers/           # query.py, debug.py (diagnostics)
main.py              # FastAPI app entry
.env.example
requirements.txt
tests/

````

---

## Prerequisites
- Python **3.11+**
- Git
- A Google Calendar you can access (ICS URL)

---

## Setup (local)

> PowerShell (Windows) shown. On macOS/Linux, adjust venv activation accordingly.

### 1️⃣ Create & activate venv
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
````

### 2️⃣ Install runtime deps

```powershell
pip install -r requirements.txt
```

### 3️⃣ Create `.env` from template

```powershell
Copy-Item .env.example .env
```

### 4️⃣ Get your ICS URL (very important)

Google Calendar → **Settings** → select your calendar → **Integrate calendar**

Use **Secret address in iCal format** (e.g.):

```
https://calendar.google.com/calendar/ical/<your-id>/private-<long-token>/basic.ics
```

> Public links require “Make available to public”; otherwise return HTML/404.

### 5️⃣ Configure `.env`

```
APP_ENV=local
DEFAULT_TZ=America/Chicago
WORK_HOURS_START=09:00
WORK_HOURS_END=18:00
AVAILABILITY_EDGE_POLICY=exclusive

# Providers
CALENDAR_ICS_URL=YOUR_SECRET_ICS_URL_HERE
GITHUB_TOKEN=
NOTION_TOKEN=
OPENAI_API_KEY=
```

---

## Run

```powershell
# ensure venv active
.\.venv\Scripts\Activate.ps1

python -m uvicorn src.app.main:app --reload --port 8000
```

Open Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## Quick Checks (M3)

| Endpoint                  | Example                                                               | Purpose                   |
| ------------------------- | --------------------------------------------------------------------- | ------------------------- |
| `/healthz`                | ✅                                                                     | Liveness                  |
| `/version`                | ✅                                                                     | Build tag                 |
| `/debug/settings`         | ✅                                                                     | Environment snapshot      |
| `/debug/providers`        | ✅                                                                     | Provider list             |
| `/debug/calendar?limit=5` | ✅                                                                     | Recent events             |
| `/debug/calendar/diag`    | ✅                                                                     | Fetch & parse diagnostics |
| **`POST /query`**         | `{ "query": "am I free tomorrow at 09:15?", "sources":["calendar"] }` | Full intent pipeline      |

---

## Example Queries (24-hour clock)

| Query                                    | Expected Result                       |
| ---------------------------------------- | ------------------------------------- |
| `am I free tomorrow at 03:10?`           | **busy** – conflicts with 03–04 event |
| `am I free tomorrow at 11:30?`           | **free**                              |
| `any slot tomorrow morning for 45 min`   | **busy**, suggests 10:00–10:45        |
| `any slot tomorrow afternoon for 30 min` | **free**, suggests 13:30–14:00        |
| `book 30 min after 15:00 today`          | **unknown**, suggests 15:30–16:00     |
| `check my schedule`                      | **unknown**, no specific window       |
| `am I free on Dec 5 at 14:00?`           | **unknown**, outside ICS horizon      |

---

### Response Shapes

**Busy point**

```json
{
  "availability": "busy",
  "conflicts": [
    { "title": "test1", "start": "...09:00...", "end": "...10:00..." }
  ],
  "explanation": "Conflicts with test1 at 09:00."
}
```

**Busy range + suggestions**

```json
{
  "availability": "busy",
  "explanation": "Conflicts with test1 09:00–10:00.",
  "suggested_slots": [
    { "start": "2025-11-10T10:00:00-06:00", "end": "2025-11-10T10:45:00-06:00" }
  ]
}
```

**Free with suggestions**

```json
{
  "availability": "free",
  "explanation": "Window is free; suggested earliest slots.",
  "suggested_slots": [
    { "start": "2025-11-10T13:30:00-06:00", "end": "2025-11-10T14:00:00-06:00" }
  ]
}
```

---

## Testing

```bash
pytest tests -q
```

Covers:

* time parsing (24 h)
* overlap logic (inclusive/exclusive edges)
* all-day and multi-day events
* after-time slot suggestions
* day-window durations & work-hour boundaries

---

## Troubleshooting

**ICS 404 / HTML**

* Wrong URL → use **Secret iCal** address.

**Wrong time zone**

* Google Calendar → General → Time Zone.

**500 error**

* Call `/debug/calendar/diag` for fetch stage details.

---

## Milestone Status

| Milestone | Description                                  | Status |
| --------- | -------------------------------------------- | ------ |
| **M0**    | Scaffold / core                              | ✅      |
| **M1**    | Diagnostics                                  | ✅      |
| **M2**    | Calendar ICS provider                        | ✅      |
| **M3**    | Availability + slot suggestion engine (24 h) | ✅      |

---

## Requirements.txt

```txt
fastapi>=0.115.0
uvicorn[standard]>=0.30.0
pydantic>=2.7.0
pydantic-settings>=2.3.0
httpx>=0.27.0
icalendar>=5.0.12
python-dateutil>=2.9.0.post0
tzdata>=2024.1
```

---

