import json
import logging
from typing import Any

import redis

from src.config.settings import settings

WORKSPACE_TTL_SECONDS = 24 * 60 * 60
logger = logging.getLogger(__name__)


def workspace_key(task_id: str) -> str:
    return f"task:{task_id}:workspace"


def redis_client() -> redis.Redis:
    return redis.Redis.from_url(
        settings.redis_url, decode_responses=True, socket_timeout=2, socket_connect_timeout=2
    )


def write_workspace(task_id: str, data: dict[str, Any]) -> None:
    redis_client().set(workspace_key(task_id), json.dumps(data, ensure_ascii=False))


def read_workspace(task_id: str) -> dict[str, Any] | None:
    value = redis_client().get(workspace_key(task_id))
    return json.loads(value) if value else None


def save_graph_state(task_id: str, data: dict[str, Any]) -> None:
    redis_client().set(f"task:{task_id}:graph-state", json.dumps(data, ensure_ascii=False))


def read_graph_state(task_id: str) -> dict[str, Any] | None:
    value = redis_client().get(f"task:{task_id}:graph-state")
    return json.loads(value) if value else None


def increment_tool_attempt(task_id: str, query: str) -> int:
    key = f"task:{task_id}:tool-attempt:{query}"
    client = redis_client()
    return int(
        client.eval(
            "local n=redis.call('INCR', KEYS[1]); redis.call('EXPIRE', KEYS[1], ARGV[1]); return n",
            1,
            key,
            WORKSPACE_TTL_SECONDS,
        )
    )


def set_engine(task_id: str, engine: str) -> None:
    redis_client().set(f"task:{task_id}:workflow-engine", engine, ex=WORKSPACE_TTL_SECONDS)


def get_engine(task_id: str) -> str | None:
    return redis_client().get(f"task:{task_id}:workflow-engine")


def set_terminal_ttl(task_id: str, ttl: int = WORKSPACE_TTL_SECONDS) -> None:
    try:
        client = redis_client()
        client.expire(workspace_key(task_id), ttl)
        client.expire(f"task:{task_id}:graph-state", ttl)
        client.expire(f"task:{task_id}:workflow-engine", ttl)
    except Exception:
        logger.warning(
            "Could not set terminal workspace retention",
            extra={
                "task_id": task_id,
                "agent_name": "System",
                "action_details": "Workspace retention update failed",
            },
        )


def publish_status(task_id: str, status: str) -> None:
    payload = json.dumps({"task_id": task_id, "status": status})
    try:
        redis_client().publish(f"task:{task_id}:events", payload)
    except Exception:
        logger.warning(
            "Could not publish workflow status",
            extra={
                "task_id": task_id,
                "agent_name": "System",
                "action_details": "Redis status publish failed",
            },
        )


def redis_ping() -> bool:
    try:
        return bool(redis_client().ping())
    except Exception:
        return False
