from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

TaskStatus = Literal[
    "PENDING", "RUNNING", "AWAITING_APPROVAL", "AWAITING_TOOL_APPROVAL", "RESUMED", "COMPLETED", "FAILED", "REJECTED"
]


class TaskCreate(BaseModel):
    prompt: str = Field(min_length=1, max_length=4000)

    @field_validator("prompt")
    @classmethod
    def prompt_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Prompt cannot be blank")
        return value.strip()


class TaskAccepted(BaseModel):
    task_id: UUID
    status: TaskStatus


class ApprovalRequest(BaseModel):
    approved: bool
    feedback: str = Field(default="", max_length=2000)


class ApprovalResponse(BaseModel):
    task_id: UUID
    status: TaskStatus


class AuditEntry(BaseModel):
    agent: str
    action: str
    timestamp: str


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    prompt: str
    status: TaskStatus
    result: str | None
    agent_logs: list[AuditEntry] | None
    created_at: datetime
    updated_at: datetime


class TaskListResponse(BaseModel):
    items: list[TaskResponse]
    total: int
    limit: int
    offset: int


class WorkspaceResponse(BaseModel):
    task_id: UUID
    workspace: dict[str, Any]


class ActivityEntry(BaseModel):
    timestamp: str
    task_id: str
    agent_name: str
    action_details: str
    level: str = "INFO"
    event: str | None = None


class ActivityResponse(BaseModel):
    task_id: UUID
    entries: list[ActivityEntry]


class CurrentUser(BaseModel):
    id: UUID
    issuer: str
    subject: str
    email: str
    display_name: str | None = None


class SessionResponse(BaseModel):
    user: CurrentUser
    csrf_token: str


class SourceArtifact(BaseModel):
    id: UUID
    title: str
    url: str
    domain: str
    retrieved_at: datetime
    excerpt: str
    status: str

    model_config = ConfigDict(from_attributes=True)


class SourcesResponse(BaseModel):
    task_id: UUID
    sources: list[SourceArtifact]


class FeedbackRequest(BaseModel):
    rating: Literal["helpful", "unhelpful"]
    comment: str | None = Field(default=None, max_length=1000)


class FeedbackResponse(BaseModel):
    saved: bool


class ToolApprovalRequest(BaseModel):
    approved: bool


class ToolApprovalItem(BaseModel):
    call_id: str
    tool_name: str
    arguments: dict[str, Any]
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ToolApprovalResponse(BaseModel):
    task_id: UUID
    call_id: str
    status: str


class RuntimeSettingsResponse(BaseModel):
    llm_provider: str
    llm_model: str
    llm_configured: bool
    search_provider: str
    search_configured: bool


class DependencyStatus(BaseModel):
    status: Literal["ok", "down"]


class SystemStatusResponse(BaseModel):
    api: Literal["ok", "down"]
    database: Literal["ok", "down"]
    redis: Literal["ok", "down"]
    worker: Literal["ok", "down"]
    version: str
    uptime_seconds: int


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: list[dict[str, Any]] | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail
