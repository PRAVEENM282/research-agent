from typing import Any

from temporalio import activity

from src.agents.research_agent import ResearchAgent
from src.agents.writing_agent import WritingAgent
from src.db.repository import execute_pending_tool_sync
from src.workflows.services import fail_task, transition


@activity.defn
def mark_running(task_id: str) -> None:
    transition(task_id, "RUNNING", agent="System", action="Temporal workflow started.")


@activity.defn
def research(task_id: str, prompt: str) -> dict[str, Any]:
    return ResearchAgent().run(task_id, prompt)


@activity.defn
def await_tool_approval(task_id: str, approval: dict[str, Any]) -> None:
    transition(
        task_id,
        "AWAITING_TOOL_APPROVAL",
        agent="System",
        action=f"Waiting for approval to call {str(approval.get('tool_name', 'connected tool'))[:180]}.",
    )


@activity.defn
def resolve_tool_approval(task_id: str, call_id: str, approved: bool) -> dict[str, Any]:
    if approved:
        return execute_pending_tool_sync(task_id, call_id)
    return {"status": "REJECTED", "content": {"denied": True}}


@activity.defn
def write_draft(task_id: str, prompt: str) -> str:
    return WritingAgent().run(task_id, prompt)


@activity.defn
def await_approval(task_id: str, draft: str) -> None:
    transition(
        task_id,
        "AWAITING_APPROVAL",
        result=draft,
        agent="System",
        action="Draft is ready; Temporal workflow is waiting for human approval.",
    )


@activity.defn
def finalize(task_id: str, draft: str, feedback: str) -> str:
    result = draft.strip()
    if feedback.strip():
        result += f"\n\nHuman review note: {feedback.strip()[:1000]}"
    transition(
        task_id,
        "COMPLETED",
        result=result,
        agent="System",
        action="Human-approved draft was saved as the final result.",
    )
    return result


@activity.defn
def reject(task_id: str) -> None:
    transition(task_id, "REJECTED", agent="System", action="Human rejected the draft.")


@activity.defn
def workflow_failed(task_id: str) -> None:
    fail_task(
        task_id, "Workflow failed after bounded retries. Check service health and retry the task."
    )
