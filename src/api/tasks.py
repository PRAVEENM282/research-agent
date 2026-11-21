import asyncio
import json
import logging
from collections import deque
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from redis.asyncio import Redis

from src.agents.scratchpad import set_engine
from src.api.schemas import (
    ActivityEntry,
    ActivityResponse,
    TaskAccepted,
    TaskCreate,
    TaskListResponse,
    TaskResponse,
    WorkspaceResponse,
    SourcesResponse,
)
from src.api.dependencies import require_csrf, require_user
from src.config.settings import settings
from src.db.repository import create_task as persist_task
from src.db.repository import get_owned_task, list_owned_tasks, list_task_sources
from src.db.models import User
from src.worker.dispatch import deliver_for_task

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])
logger = logging.getLogger(__name__)


async def enforce_submission_limit(request: Request, user_id: str) -> None:
    key = f"rate:task-create:{user_id}"
    client = Redis.from_url(
        settings.redis_url, decode_responses=True, socket_timeout=2, socket_connect_timeout=2
    )
    try:
        count = int(
            await client.eval(
                "local c=redis.call('INCR', KEYS[1]); if c==1 then redis.call('EXPIRE', KEYS[1], ARGV[1]); end; return c",
                1,
                key,
                settings.rate_limit_window_seconds,
            )
        )
    except Exception as exc:
        logger.warning(
            "Task rate limiter unavailable",
            extra={
                "task_id": "",
                "agent_name": "System",
                "action_details": "Task rate limiter unavailable",
            },
        )
        raise HTTPException(503) from exc
    finally:
        await client.aclose()
    if count > settings.rate_limit_max_requests:
        raise HTTPException(429)


@router.post("", response_model=TaskAccepted, status_code=status.HTTP_202_ACCEPTED)
async def create_task(
    body: TaskCreate,
    request: Request,
    background: BackgroundTasks,
    user: User = Depends(require_user),
    _: None = Depends(require_csrf),
) -> TaskAccepted:
    await enforce_submission_limit(request, str(user.id))
    task = await persist_task(body.prompt, user.id)
    await asyncio.to_thread(set_engine, str(task.id), settings.workflow_engine)
    background.add_task(deliver_for_task, task.id)
    return TaskAccepted(task_id=task.id, status="PENDING")


@router.get("", response_model=TaskListResponse)
async def list_task_route(
    status_filter: Annotated[
        str | None,
        Query(
            alias="status",
            pattern="^(PENDING|RUNNING|AWAITING_APPROVAL|AWAITING_TOOL_APPROVAL|RESUMED|COMPLETED|FAILED|REJECTED)$",
        ),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0, le=100000)] = 0,
    user: User = Depends(require_user),
) -> TaskListResponse:
    items, total = await list_owned_tasks(user.id, status_filter, limit, offset)
    return TaskListResponse(
        items=[TaskResponse.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task_route(task_id: UUID, user: User = Depends(require_user)) -> TaskResponse:
    task = await get_owned_task(task_id, user.id)
    if task is None:
        raise HTTPException(404)
    return TaskResponse.model_validate(task)


@router.get("/{task_id}/workspace", response_model=WorkspaceResponse)
async def get_workspace(task_id: UUID, user: User = Depends(require_user)) -> WorkspaceResponse:
    if await get_owned_task(task_id, user.id) is None:
        raise HTTPException(404)
    client = Redis.from_url(
        settings.redis_url, decode_responses=True, socket_timeout=2, socket_connect_timeout=2
    )
    try:
        raw = await client.get(f"task:{task_id}:workspace")
    finally:
        await client.aclose()
    if raw is None:
        raise HTTPException(
            404,
            detail={"code": "workspace_expired", "message": "The shared workspace has expired."},
        )
    try:
        workspace = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(503) from exc
    return WorkspaceResponse(task_id=task_id, workspace=workspace)


@router.get("/{task_id}/activity", response_model=ActivityResponse)
async def get_activity(
    task_id: UUID,
    limit: Annotated[int, Query(ge=1, le=500)] = 200,
    user: User = Depends(require_user),
) -> ActivityResponse:
    if await get_owned_task(task_id, user.id) is None:
        raise HTTPException(404)
    log_path = Path(__import__("os").getenv("LOG_DIR", "logs")) / "agent_activity.log"

    def read_tail() -> list[dict[str, str]]:
        if not log_path.exists():
            return []
        lines: deque[str] = deque(maxlen=500)
        with log_path.open("r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                lines.append(line)
        entries: list[dict[str, str]] = []
        for line in list(lines)[-limit:]:
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if entry.get("task_id") == str(task_id):
                entries.append(
                    {
                        key: str(entry.get(key, ""))
                        for key in (
                            "timestamp",
                            "task_id",
                            "agent_name",
                            "action_details",
                            "level",
                            "event",
                        )
                    }
                )
        return entries

    entries = await asyncio.to_thread(read_tail)
    return ActivityResponse(
        task_id=task_id, entries=[ActivityEntry.model_validate(entry) for entry in entries]
    )


@router.get("/{task_id}/sources", response_model=SourcesResponse)
async def get_sources(task_id: UUID, user: User = Depends(require_user)) -> SourcesResponse:
    if await get_owned_task(task_id, user.id) is None:
        raise HTTPException(404)
    return SourcesResponse(task_id=task_id, sources=await list_task_sources(task_id))
