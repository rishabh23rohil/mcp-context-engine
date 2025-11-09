from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from .logging import get_logger
from .config import settings
import traceback

log = get_logger(__name__)

def install_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        # Always log full details to console
        log.exception("unhandled.exception")

        if settings.APP_ENV == "local":
            # In local mode, show rich diagnostics
            return JSONResponse(
                status_code=500,
                content={
                    "error": "internal_server_error",
                    "type": exc.__class__.__name__,
                    "message": str(exc),
                    "trace": traceback.format_exc(),
                },
            )

        # In non-local, keep it generic
        return JSONResponse(
            status_code=500,
            content={"error": "internal_server_error", "detail": "Something went wrong."},
        )
