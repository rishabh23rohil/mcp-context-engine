# MCP Context Engine

FastAPI-based context server for AI assistants.

## Run

```bash
uv venv
uv pip install -e ".[dev]"
# Windows friendly copy for .env:
copy .env.example .env
uvicorn src.app.main:app --reload --port 8000
