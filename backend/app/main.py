import logging
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api import analytics, chat, dl, nlp, system
from .core import db
from .core.config import settings
from .core.errors import AppError

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("nexora")


def cleanup_uploads() -> None:
    """Delete uploaded datasets older than UPLOAD_TTL_HOURS."""
    cutoff = datetime.now().timestamp() - timedelta(hours=settings.upload_ttl_hours).total_seconds()
    for f in settings.upload_dir.glob("*.csv"):
        if f.stat().st_mtime < cutoff:
            f.unlink(missing_ok=True)


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.init()
    cleanup_uploads()
    yield


app = FastAPI(title="Nexora AI", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["*"], allow_headers=["*"],
                   expose_headers=["X-Conversation-Id", "X-Provider"])

_hits: dict[str, deque] = defaultdict(deque)


@app.middleware("http")
async def rate_limit(request: Request, call_next):
    """Simple in-memory per-IP limiter (single process). Use a shared store when deploying several workers."""
    if request.url.path != "/api/health":
        ip = request.client.host if request.client else "unknown"
        q, now = _hits[ip], time.time()
        while q and now - q[0] > 60:
            q.popleft()
        if len(q) >= settings.rate_limit_per_min:
            return JSONResponse({"error": {"code": "rate_limited", "message": "Too many requests. Slow down."}}, 429)
        q.append(now)
    return await call_next(request)


@app.exception_handler(AppError)
async def app_error(_: Request, e: AppError):
    return JSONResponse({"error": {"code": e.code, "message": e.message}}, e.status)


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, e: RequestValidationError):
    first = e.errors()[0] if e.errors() else {}
    where = ".".join(str(p) for p in first.get("loc", []) if p != "body")
    return JSONResponse({"error": {"code": "invalid_request", "message": f"Invalid input ({where}): {first.get('msg', '')}"}}, 422)


@app.exception_handler(Exception)
async def unexpected(request: Request, e: Exception):
    log.error("Unhandled error on %s %s: %s", request.method, request.url.path, type(e).__name__)  # no payloads logged
    return JSONResponse({"error": {"code": "server_error", "message": "Something went wrong on the server."}}, 500)


for r in (system.router, chat.router, nlp.router, analytics.router, dl.router):
    app.include_router(r)
