from src.agents.scratchpad import publish_status, set_terminal_ttl
from src.db.repository import set_task_status


def transition(
    task_id: str,
    status: str,
    *,
    result: str | None = None,
    agent: str = "System",
    action: str | None = None,
) -> None:
    description = action or f"Task status changed to {status}."
    set_task_status(task_id, status, result=result, audit=(agent, description))
    publish_status(task_id, status)
    if status in {"COMPLETED", "FAILED", "REJECTED"}:
        set_terminal_ttl(task_id)
    from src.config.logging_config import activity_log

    activity_log(task_id, agent, description)


def fail_task(task_id: str, reason: str) -> None:
    safe_reason = reason[:500]
    transition(task_id, "FAILED", result=safe_reason, action=f"Workflow failed: {safe_reason}")
