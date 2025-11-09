from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from .logging import get_logger

log = get_logger(__name__)

def install_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        log.exception("unhandled.exception")
        return JSONResponse(
            status_code=500,
            content={"error": "internal_server_error", "detail": "Something went wrong."},
        )
