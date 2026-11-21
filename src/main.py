import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware

from src.api.approvals import router as approvals_router
from src.api.auth import router as auth_router
from src.api.connections import router as connections_router
from src.api.errors import error_body, install_error_handlers
from src.api.feedback import router as feedback_router
from src.api.settings import router as settings_router
from src.api.tasks import router as tasks_router
from src.api.websocket import router as websocket_router
from src.config.logging_config import configure_logging
from src.config.settings import settings
from src.db.engine import close_engines, init_db
from src.db.repository import persist_demo_task

configure_logging(settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    if settings.seed_demo_data:
        import asyncio

        await asyncio.to_thread(persist_demo_task)
    app.state.started_at = time.monotonic()
    yield
    await close_engines()


app = FastAPI(
    title="Handoff",
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/api/reference",
    redoc_url="/api/redoc",
    openapi_url="/openapi.json",
)
install_error_handlers(app)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.oidc_session_secret or "development-only-handoff-session-key-change-me",
    session_cookie="handoff_oidc",
    max_age=600,
    same_site="lax",
    https_only=settings.session_cookie_secure,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-CSRF-Token"],
)


@app.middleware("http")
async def secure_responses(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if (
        content_length
        and content_length.isdigit()
        and int(content_length) > settings.max_request_bytes
    ):
        return JSONResponse(
            error_body("request_too_large", "The request body is too large."), status_code=413
        )
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if not request.url.path.startswith(("/api/reference", "/api/redoc")):
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; connect-src 'self' ws: wss:; frame-ancestors 'none'; base-uri 'self'"
        )
    return response


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(tasks_router)
app.include_router(approvals_router)
app.include_router(auth_router)
app.include_router(settings_router)
app.include_router(feedback_router)
app.include_router(connections_router)
app.include_router(websocket_router)
