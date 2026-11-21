import asyncio
import time

from fastapi import APIRouter

from src.api.events import async_redis_ping
from src.api.schemas import SystemStatusResponse
from src.config.settings import settings
from src.db.engine import database_ping

router = APIRouter(prefix="/api/v1/system", tags=["system"])
_started_at = time.monotonic()


def _worker_ping() -> bool:
    try:
        from src.worker.celery_app import celery_app

        replies = celery_app.control.inspect(timeout=settings.celery_probe_timeout_seconds).ping()
        return bool(replies)
    except Exception:
        return False


@router.get("/status", response_model=SystemStatusResponse)
async def system_status() -> SystemStatusResponse:
    db_ok, redis_ok, worker_ok = await asyncio.gather(
        database_ping(), async_redis_ping(), asyncio.to_thread(_worker_ping)
    )
    return SystemStatusResponse(
        api="ok",
        database="ok" if db_ok else "down",
        redis="ok" if redis_ok else "down",
        worker="ok" if worker_ok else "down",
        version=settings.app_version,
        uptime_seconds=max(0, int(time.monotonic() - _started_at)),
    )
