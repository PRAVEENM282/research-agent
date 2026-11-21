from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi import Depends

from src.api.events import publish_status_async
from src.api.schemas import ApprovalRequest, ApprovalResponse
from src.db.repository import approve_task
from src.api.dependencies import require_csrf, require_user
from src.api.schemas import ToolApprovalItem, ToolApprovalRequest, ToolApprovalResponse
from src.db.models import User
from src.db.repository import approve_tool_call, list_tool_approvals
from src.worker.dispatch import deliver_for_task

router = APIRouter(prefix="/api/v1/tasks", tags=["approvals"])


@router.post("/{task_id}/approve", response_model=ApprovalResponse)
async def approve_route(
    task_id: UUID,
    body: ApprovalRequest,
    background: BackgroundTasks,
    user: User = Depends(require_user),
    _: None = Depends(require_csrf),
) -> ApprovalResponse:
    result = await approve_task(task_id, user.id, body.approved, body.feedback.strip())
    if result is None:
        raise HTTPException(404)
    if result == "CONFLICT":
        raise HTTPException(409)
    await publish_status_async(task_id, result)
    if result in {"RESUMED", "REJECTED"}:
        background.add_task(deliver_for_task, task_id)
    return ApprovalResponse(task_id=task_id, status=result)


@router.get("/{task_id}/tool-approvals", response_model=list[ToolApprovalItem])
async def list_tool_approval_route(
    task_id: UUID, user: User = Depends(require_user)
) -> list[ToolApprovalItem]:
    rows = await list_tool_approvals(task_id, user.id)
    if rows is None:
        raise HTTPException(404)
    return [ToolApprovalItem.model_validate(row) for row in rows]


@router.post(
    "/{task_id}/tool-approvals/{call_id}",
    response_model=ToolApprovalResponse,
    dependencies=[Depends(require_csrf)],
)
async def decide_tool_approval_route(
    task_id: UUID,
    call_id: str,
    body: ToolApprovalRequest,
    background: BackgroundTasks,
    user: User = Depends(require_user),
) -> ToolApprovalResponse:
    result = await approve_tool_call(task_id, user.id, call_id, body.approved)
    if result is None:
        raise HTTPException(404)
    if result == "CONFLICT":
        raise HTTPException(409)
    await publish_status_async(task_id, "RESUMED")
    background.add_task(deliver_for_task, task_id)
    return ToolApprovalResponse(task_id=task_id, call_id=call_id, status=result)
