import asyncio
import json
import logging
from uuid import UUID

from redis.asyncio import Redis

from src.agents.scratchpad import publish_status, set_terminal_ttl
from src.config.settings import settings

logger = logging.getLogger(__name__)


async def publish_status_async(task_id: UUID | str, status: str) -> None:
    try:
        await asyncio.to_thread(publish_status, str(task_id), status)
        if status in {"COMPLETED", "FAILED", "REJECTED"}:
            await asyncio.to_thread(set_terminal_ttl, str(task_id))
    except Exception:
        logger.warning(
            "Could not publish task status event",
            extra={
                "task_id": str(task_id),
                "agent_name": "System",
                "action_details": "Status event publish failed",
            },
        )


def status_redis() -> Redis:
    return Redis.from_url(
        settings.redis_url, decode_responses=True, socket_timeout=3, socket_connect_timeout=2
    )


async def async_redis_ping() -> bool:
    client = status_redis()
    try:
        return bool(await client.ping())
    except Exception:
        return False
    finally:
        await client.aclose()


def websocket_message(task_id: UUID, status: str) -> str:
    return json.dumps({"task_id": str(task_id), "status": status})
