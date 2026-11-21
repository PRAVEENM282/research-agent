from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from src.api.dependencies import require_csrf, require_user
from src.api.schemas import FeedbackRequest, FeedbackResponse
from src.db.models import User
from src.db.repository import save_feedback

router = APIRouter(prefix="/api/v1/tasks", tags=["feedback"])


@router.post("/{task_id}/feedback", response_model=FeedbackResponse, dependencies=[Depends(require_csrf)])
async def submit_feedback(
    task_id: UUID, body: FeedbackRequest, user: User = Depends(require_user)
) -> FeedbackResponse:
    await save_feedback(task_id, user.id, body.rating, body.comment.strip() if body.comment else None)
    # The repository intentionally uses the same response for missing and non-owned IDs.
    from src.db.repository import get_owned_task

    if await get_owned_task(task_id, user.id) is None:
        raise HTTPException(404)
    return FeedbackResponse(saved=True)
