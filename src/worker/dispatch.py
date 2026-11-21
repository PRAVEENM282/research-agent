import logging
from uuid import UUID

from src.db.repository import claim_outbox, mark_outbox_delivered, outbox_pending, release_outbox

logger = logging.getLogger(__name__)


def deliver_outbox(outbox_id: UUID) -> bool:
    entry = claim_outbox(outbox_id)
    if entry is None:
        return False
    try:
        from src.worker.tasks import resume_agent_workflow, run_agent_workflow

        if entry["kind"] == "resume":
            resume_agent_workflow.delay(
                str(entry["task_id"]), bool(entry["approved"]), entry["feedback"] or ""
            )
        elif entry["kind"] == "tool_resume":
            from src.worker.tasks import resume_tool_workflow

            resume_tool_workflow.delay(
                str(entry["task_id"]), entry["call_id"], bool(entry["approved"])
            )
        else:
            run_agent_workflow.delay(str(entry["task_id"]), entry["prompt"])
        mark_outbox_delivered(entry["id"])
        return True
    except Exception as exc:
        release_outbox(entry["id"])
        logger.warning(
            "Workflow dispatch deferred for retry",
            extra={
                "task_id": str(entry["task_id"]),
                "agent_name": "System",
                "action_details": f"Broker dispatch failed: {type(exc).__name__}",
            },
        )
        return False


def drain_outbox() -> int:
    delivered = 0
    for row in outbox_pending():
        if deliver_outbox(row["id"]):
            delivered += 1
    return delivered


def deliver_for_task(task_id: UUID) -> None:
    for row in outbox_pending():
        if row["task_id"] == task_id:
            deliver_outbox(row["id"])
