from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        Index("ix_tasks_created_at_desc", text("created_at DESC")),
        Index("ix_tasks_status", "status"),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    agent_logs: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("NOW()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("NOW()")
    )


class DispatchOutbox(Base):
    """Durable handoff from the API transaction to the broker."""

    __tablename__ = "task_dispatch_outbox"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    task_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, index=True)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    kind: Mapped[str] = mapped_column(String(20), nullable=False, server_default="run")
    approved: Mapped[bool | None] = mapped_column(nullable=True)
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    call_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("NOW()")
    )


class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("issuer", "subject", name="uq_users_issuer_subject"),)

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    issuer: Mapped[str] = mapped_column(Text, nullable=False)
    subject: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("NOW()")
    )


class UserSession(Base):
    __tablename__ = "user_sessions"
    __table_args__ = (Index("ix_user_sessions_user_expires", "user_id", "expires_at"),)

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("NOW()")
    )


class TaskOwner(Base):
    __tablename__ = "task_owners"
    __table_args__ = (Index("ix_task_owners_user", "user_id", "task_id"),)

    task_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("NOW()")
    )


class TaskSource(Base):
    __tablename__ = "task_sources"
    __table_args__ = (
        UniqueConstraint("task_id", "url", name="uq_task_sources_task_url"),
        Index("ix_task_sources_task_created", "task_id", "retrieved_at"),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    task_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    domain: Mapped[str] = mapped_column(String(253), nullable=False)
    retrieved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("NOW()")
    )
    excerpt: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="EXTRACTED")
    extraction_error: Mapped[str | None] = mapped_column(String(120), nullable=True)


class TaskFeedback(Base):
    __tablename__ = "task_feedback"
    __table_args__ = (
        UniqueConstraint("task_id", "user_id", name="uq_task_feedback_owner"),
        CheckConstraint("rating IN ('helpful', 'unhelpful')", name="ck_task_feedback_rating"),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    task_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    rating: Mapped[str] = mapped_column(String(16), nullable=False)
    comment: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("NOW()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("NOW()")
    )


class MCPConnection(Base):
    __tablename__ = "mcp_connections"
    __table_args__ = (Index("ix_mcp_connections_user", "user_id", "created_at"),)

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    server_url: Mapped[str] = mapped_column(Text, nullable=False)
    encrypted_bearer_token: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    enabled_tools: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    read_only_tools: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("NOW()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("NOW()")
    )


class PendingToolApproval(Base):
    __tablename__ = "pending_tool_approvals"
    __table_args__ = (
        UniqueConstraint("task_id", "call_id", name="uq_pending_tool_approval_call"),
        Index("ix_pending_tool_approvals_task_status", "task_id", "status"),
        Index("ix_pending_tool_approvals_task_hash", "task_id", "arguments_hash"),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    task_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    owner_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    call_id: Mapped[str] = mapped_column(String(200), nullable=False)
    tool_name: Mapped[str] = mapped_column(String(200), nullable=False)
    connection_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("mcp_connections.id", ondelete="SET NULL"), nullable=True
    )
    remote_tool_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    arguments: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    arguments_hash: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    encrypted_arguments: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING_APPROVAL")
    result: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("NOW()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("NOW()")
    )
