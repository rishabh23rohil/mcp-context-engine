from fastapi import FastAPI
from .core.config import settings
from .core.logging import get_logger
from .core.errors import install_exception_handlers
from .routers.query import router as query_router
from .routers.debug import router as debug_router

log = get_logger(__name__)

app = FastAPI(title="MCP Context Engine", version="0.0.1", docs_url="/docs", redoc_url="/redoc")

@app.get("/healthz")
def healthz() -> dict:
    return {"ok": True}

@app.get("/version")
def version() -> dict:
    return {"service": "mcp-context-engine", "version": app.version, "env": settings.APP_ENV}

app.include_router(query_router)
app.include_router(debug_router, prefix="/debug")  # <-- prefix only here

install_exception_handlers(app)

@app.on_event("startup")
async def on_startup() -> None:
    log.info(f"service.startup env={settings.APP_ENV}")

@app.on_event("shutdown")
async def on_shutdown() -> None:
    log.info("service.shutdown")
