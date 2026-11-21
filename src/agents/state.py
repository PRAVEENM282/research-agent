from typing import TypedDict


class AgentState(TypedDict, total=False):
    task_id: str
    prompt: str
    findings_key: str
    draft: str
    errors: list[str]
    approved: bool
    feedback: str
    final_result: str
    findings: dict[str, object]
    pending_approval: dict[str, object] | None
    resume_tool: bool
