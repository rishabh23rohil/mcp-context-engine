Got you. Here’s everything for **Milestone 2**—clean and copy-paste ready.

# 1) `README.md`

```md
# MCP Context Engine

A minimal **context-aware middleware** (MCP-style) that fetches real-world data and outputs AI-ready context.  
**Milestones complete:**  
- **M0** – FastAPI scaffold, config, logging, error handling  
- **M1** – Health & diagnostics routes  
- **M2** – Google Calendar (ICS) provider with diagnostics & event listing

---

## Stack
- Python 3.11+ (works on 3.13)
- FastAPI + Uvicorn
- httpx, icalendar
- pydantic-settings for `.env`

---

## Repo layout (key)
```

src/
app/
core/              # config, logging, error handling
providers/         # calendar_ics.py (M2)
routers/           # query.py, debug.py (diagnostics)
main.py            # FastAPI app (mounts routers)
.env.example
requirements.txt

````

---

## Prerequisites
- Python **3.11+**
- Git
- A Google Calendar you can access

---

## Setup (local)

> PowerShell (Windows) shown. On macOS/Linux, adjust venv activation accordingly.

1) **Create & activate venv**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
````

2. **Install runtime deps**

```powershell
pip install -r requirements.txt
```

3. **Create `.env` from template**

```powershell
Copy-Item .env.example .env
```

4. **Get your ICS URL (very important)**
   Google Calendar → **Settings** → pick your calendar under **My calendars** → **Integrate calendar**:

* Prefer **Secret address in iCal format** (works without making calendar public).
  Looks like:
  `https://calendar.google.com/calendar/ical/<your-id>/private-<long-token>/basic.ics`

> If you use *Public address in iCal format*, you must first enable
> **Access permissions → Make available to public**. Otherwise the URL returns HTML/404 (not ICS).

5. **Configure `.env`**

```
APP_ENV=local
CALENDAR_ICS_URL=YOUR_SECRET_ICS_URL_HERE
GITHUB_TOKEN=
NOTION_TOKEN=
OPENAI_API_KEY=
```

---

## Run

```powershell
# ensure venv is active
.\.venv\Scripts\Activate.ps1

python -m uvicorn src.app.main:app --reload --port 8000
```

Server: [http://127.0.0.1:8000](http://127.0.0.1:8000)

---

## Quick checks (Milestone 2)

Open in a browser or curl:

* Health:
  `GET http://127.0.0.1:8000/healthz`
  → `{"ok": true}`

* Version:
  `GET http://127.0.0.1:8000/version`

* Provider selection:
  `GET http://127.0.0.1:8000/debug/providers`
  → `{"calendar":"CalendarICSProvider"}`

* Settings (redacted):
  `GET http://127.0.0.1:8000/debug/settings`
  → confirms `CALENDAR_ICS_URL_set: true`

* ICS diagnostics:
  `GET http://127.0.0.1:8000/debug/calendar/diag`

  * ✅ Expect: `{"ok": true, "stage": "parse", "events_found": N, "fetch": {...}}`
  * ❌ If you see `status: 404` or `content-type: text/html`, you copied the wrong link. Use **Secret iCal**.

* List upcoming events (limit=10):
  `GET http://127.0.0.1:8000/debug/calendar?limit=10`
  Sample:

  ```json
  {
    "provider":"CalendarICSProvider",
    "count":2,
    "items":[
      {
        "source":"calendar",
        "title":"m2 test",
        "snippet":"2025-11-10 03:00 - 04:00 (local time)",
        "url":null,
        "metadata":{
          "start":"2025-11-10T03:00:00-06:00",
          "end":"2025-11-10T04:00:00-06:00"
        }
      }
    ]
  }
  ```

---

## Troubleshooting

**ICS 404 or HTML page**

* You copied the wrong URL. Use **Secret address in iCal format**.
* Put it in `.env` → `CALENDAR_ICS_URL=...` and save. Server will auto-reload.

**Time zone looks off**

* Google Calendar → **General → Time Zone**.
* We output local-time snippets; `metadata.start/end` are ISO with offsets.

**Generic 500**

* Check `/debug/calendar/diag` → see `"stage"` and `"fetch"` sections for the exact failure.

---

## Milestone status

* **M0**: Scaffold / core ✅
* **M1**: Diagnostics ✅
* **M2**: Calendar ICS provider + routes ✅

Next (not in this commit): **M3** (Notion/GitHub providers + merged `/query`).

---

````

---

# 2) `requirements.txt` (paste exactly)

```txt
fastapi==0.121.1
uvicorn[standard]==0.38.0
pydantic==2.12.4
pydantic-settings==2.11.0
httpx==0.28.1
icalendar==5.0.12
````

---

# 3) Push Milestone 2 to GitHub

```powershell
# from repo root
.\.venv\Scripts\Activate.ps1

# ensure runtime deps exist for teammates
pip install -r requirements.txt

# stage files (do NOT commit .env)
git add README.md requirements.txt src docs .github
git reset .env 2>$null

git commit -
```
