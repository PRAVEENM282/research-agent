import asyncio
import json
import logging
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from redis.asyncio import Redis
from sqlalchemy import select

from src.config.settings import settings
from src.db.engine import AsyncSessionFactory
from src.db.models import Task, TaskOwner, User, UserSession
from src.api.dependencies import SESSION_COOKIE, token_hash

router = APIRouter(tags=["live status"])
logger = logging.getLogger(__name__)
TERMINAL = {"COMPLETED", "FAILED", "REJECTED"}


@router.websocket("/ws/tasks/{task_id}")
async def task_events(websocket: WebSocket, task_id: UUID) -> None:
    raw_token = websocket.cookies.get(SESSION_COOKIE)
    origin = websocket.headers.get("origin", "").rstrip("/")
    expected_scheme = "https" if websocket.url.scheme == "wss" else "http"
    expected_origin = f"{expected_scheme}://{websocket.url.netloc}"
    if not raw_token or origin != expected_origin:
        await websocket.close(code=4401, reason="Sign in required")
        return
    async with AsyncSessionFactory() as session:
        row = (
            await session.execute(
                select(Task, User)
                .join(TaskOwner, TaskOwner.task_id == Task.id)
                .join(User, User.id == TaskOwner.user_id)
                .join(UserSession, UserSession.user_id == User.id)
                .where(
                    Task.id == task_id,
                    UserSession.token_hash == token_hash(raw_token),
                    UserSession.revoked_at.is_(None),
                    UserSession.expires_at > datetime.now(UTC),
                )
            )
        ).one_or_none()
    if row is None:
        await websocket.close(code=4404, reason="Task not found")
        return
    task = row[0]
    await websocket.accept()
    await websocket.send_json({"task_id": str(task_id), "status": task.status})
    if task.status in TERMINAL:
        await websocket.close(code=1000, reason="Task is complete")
        return
    client = Redis.from_url(
        settings.redis_url, decode_responses=True, socket_timeout=3, socket_connect_timeout=2
    )
    pubsub = client.pubsub()
    try:
        await pubsub.subscribe(f"task:{task_id}:events")
        while True:
            if websocket.client_state.name == "DISCONNECTED":
                break
            event = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if not event or not event.get("data"):
                await asyncio.sleep(0.05)
                continue
            try:
                payload = json.loads(event["data"])
            except (TypeError, json.JSONDecodeError):
                continue
            await websocket.send_json(payload)
            if payload.get("status") in TERMINAL:
                await websocket.close(code=1000, reason="Task is complete")
                break
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        await pubsub.unsubscribe(f"task:{task_id}:events")
        await pubsub.aclose()
        await client.aclose()
