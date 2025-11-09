from fastapi import FastAPI
from .core.config import settings
from .core.logging import get_logger
from .core.errors import install_exception_handlers
from .routers.query import router as query_router  # <-- add this

log = get_logger(__name__)
app = FastAPI(title="MCP Context Engine", version="0.0.1")

@app.get("/healthz")
def healthz() -> dict:
    return {"ok": True}

@app.get("/version")
def version() -> dict:
    return {"service": "mcp-context-engine", "version": app.version, "env": settings.app_env}

# mount the query router
app.include_router(query_router)

install_exception_handlers(app)

@app.on_event("startup")
async def on_startup() -> None:
    log.info("service.startup", extra={"env": settings.app_env})

@app.on_event("shutdown")
async def on_shutdown() -> None:
    log.info("service.shutdown")
