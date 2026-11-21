import json
import hashlib
import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import func, select, text, update

from src.db.engine import AsyncSessionFactory, SyncSessionFactory
from src.db.models import (
    DispatchOutbox,
    MCPConnection,
    PendingToolApproval,
    Task,
    TaskOwner,
    TaskSource,
)

logger = logging.getLogger(__name__)


def _stamp() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


async def create_task(prompt: str, owner_id: UUID, task_id: UUID | None = None) -> Task:
    task = Task(id=task_id or uuid4(), prompt=prompt, status="PENDING", result=None, agent_logs=[])
    async with AsyncSessionFactory() as session:
        async with session.begin():
            session.add(task)
            session.add(TaskOwner(task_id=task.id, user_id=owner_id))
            session.add(DispatchOutbox(id=uuid4(), task_id=task.id, prompt=prompt, kind="run"))
        await session.refresh(task)
    return task


async def get_task(task_id: UUID) -> Task | None:
    async with AsyncSessionFactory() as session:
        return await session.get(Task, task_id)


async def get_owned_task(task_id: UUID, owner_id: UUID) -> Task | None:
    async with AsyncSessionFactory() as session:
        return await session.scalar(
            select(Task).join(TaskOwner, TaskOwner.task_id == Task.id).where(
                Task.id == task_id, TaskOwner.user_id == owner_id
            )
        )


async def list_tasks(status: str | None, limit: int, offset: int) -> tuple[list[Task], int]:
    async with AsyncSessionFactory() as session:
        conditions = [Task.status == status] if status else []
        items = list(
            (
                await session.scalars(
                    select(Task)
                    .where(*conditions)
                    .order_by(Task.created_at.desc())
                    .limit(limit)
                    .offset(offset)
                )
            ).all()
        )
        total = int(
            await session.scalar(select(func.count()).select_from(Task).where(*conditions)) or 0
        )
        return items, total


async def list_owned_tasks(
    owner_id: UUID, status: str | None, limit: int, offset: int
) -> tuple[list[Task], int]:
    async with AsyncSessionFactory() as session:
        conditions = [TaskOwner.user_id == owner_id]
        if status:
            conditions.append(Task.status == status)
        statement = select(Task).join(TaskOwner, TaskOwner.task_id == Task.id).where(*conditions)
        items = list(
            (await session.scalars(statement.order_by(Task.created_at.desc()).limit(limit).offset(offset))).all()
        )
        total = int(
            await session.scalar(
                select(func.count()).select_from(Task).join(TaskOwner, TaskOwner.task_id == Task.id).where(*conditions)
            )
            or 0
        )
        return items, total


async def approve_task(task_id: UUID, owner_id: UUID, approved: bool, feedback: str) -> str | None:
    stamp = _stamp()
    audit = {
        "agent": "HumanApproval",
        "action": "Approved draft" if approved else f"Rejected draft: {feedback}".rstrip(),
        "timestamp": stamp,
    }
    async with AsyncSessionFactory() as session:
        async with session.begin():
            row = (
                await session.execute(
                    select(Task)
                    .join(TaskOwner, TaskOwner.task_id == Task.id)
                    .where(Task.id == task_id, TaskOwner.user_id == owner_id)
                    .with_for_update()
                )
            ).scalar_one_or_none()
            if row is None:
                return None
            if row.status != "AWAITING_APPROVAL":
                return "CONFLICT"
            new_status = "RESUMED" if approved else "REJECTED"
            conditional = await session.execute(
                text("""UPDATE tasks SET status=:status,
                    agent_logs=COALESCE(agent_logs, '[]'::jsonb) || CAST(:entry AS jsonb)
                WHERE id=:task_id AND status='AWAITING_APPROVAL' AND EXISTS (
                    SELECT 1 FROM task_owners WHERE task_id=:task_id AND user_id=:owner_id
                )"""),
                {"status": new_status, "entry": json.dumps([audit]), "task_id": task_id, "owner_id": owner_id},
            )
            if conditional.rowcount != 1:
                return "CONFLICT"
            session.add(
                DispatchOutbox(
                    id=uuid4(),
                    task_id=task_id,
                    prompt=row.prompt,
                    kind="resume",
                    approved=approved,
                    feedback=feedback,
                )
            )
    return new_status


async def list_task_sources(task_id: UUID) -> list[TaskSource]:
    async with AsyncSessionFactory() as session:
        return list(
            (await session.scalars(select(TaskSource).where(TaskSource.task_id == task_id).order_by(TaskSource.retrieved_at))).all()
        )


def save_task_source(task_id: UUID | str, source: dict[str, Any]) -> None:
    task_uuid = UUID(str(task_id))
    with SyncSessionFactory() as session, session.begin():
        existing = session.scalar(
            select(TaskSource).where(TaskSource.task_id == task_uuid, TaskSource.url == source["url"])
        )
        if existing:
            existing.title = str(source.get("title") or existing.title)[:500]
            existing.domain = str(source.get("domain") or existing.domain)[:253]
            existing.excerpt = str(source.get("excerpt") or "")[:12000]
            existing.status = str(source.get("status") or "EXTRACTED")[:32]
            existing.extraction_error = str(source.get("extraction_error") or "")[:120] or None
        else:
            retrieved_at = source.get("retrieved_at")
            if isinstance(retrieved_at, str):
                retrieved_at = datetime.fromisoformat(retrieved_at.replace("Z", "+00:00"))
            session.add(
                TaskSource(
                    task_id=task_uuid,
                    title=str(source.get("title") or "Untitled page")[:500],
                    url=str(source["url"]),
                    domain=str(source.get("domain") or "")[:253],
                    retrieved_at=retrieved_at or datetime.now(UTC),
                    excerpt=str(source.get("excerpt") or "")[:12000],
                    status=str(source.get("status") or "EXTRACTED")[:32],
                    extraction_error=str(source.get("extraction_error") or "")[:120] or None,
                )
            )


def get_task_owner_sync(task_id: str | UUID) -> UUID | None:
    with SyncSessionFactory() as session:
        return session.scalar(select(TaskOwner.user_id).where(TaskOwner.task_id == UUID(str(task_id))))


def _tool_arguments_hash(arguments: dict[str, Any]) -> str:
    encoded = json.dumps(arguments, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _redact_tool_arguments(value: Any, key: str = "") -> Any:
    if any(word in key.lower() for word in ("token", "password", "secret", "api_key", "authorization", "credential")):
        return "[redacted]"
    if isinstance(value, dict):
        return {str(item_key)[:100]: _redact_tool_arguments(item_value, str(item_key)) for item_key, item_value in list(value.items())[:80]}
    if isinstance(value, list):
        return [_redact_tool_arguments(item) for item in value[:80]]
    if isinstance(value, str):
        return value[:1000]
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return str(value)[:1000]


def resolved_tool_result(
    task_id: str | UUID, tool_name: str, arguments: dict[str, Any]
) -> dict[str, Any] | None:
    digest = _tool_arguments_hash(arguments)
    with SyncSessionFactory() as session:
        row = session.scalar(
            select(PendingToolApproval)
            .where(
                PendingToolApproval.task_id == UUID(str(task_id)),
                PendingToolApproval.tool_name == tool_name,
                PendingToolApproval.arguments_hash == digest,
                PendingToolApproval.status.in_(
                    ["SUCCEEDED", "FAILED", "REJECTED", "INDETERMINATE", "RUNNING"]
                ),
            )
            .order_by(PendingToolApproval.updated_at.desc())
        )
        if not row:
            return None
        status = "INDETERMINATE" if row.status == "RUNNING" else row.status
        content = row.result or ({"error": "execution_outcome_unknown"} if status == "INDETERMINATE" else {})
        return {"status": status, "content": content}


def create_pending_tool_approval(
    *,
    task_id: str | UUID,
    owner_id: UUID,
    call_id: str,
    tool_name: str,
    connection_id: UUID,
    remote_tool_name: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    from src.agents.mcp_client import encrypt_user_payload

    task_uuid = UUID(str(task_id))
    digest = _tool_arguments_hash(arguments)
    encoded = json.dumps(arguments, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if len(encoded) > 16_000:
        raise ValueError("Tool arguments exceeded the configured limit.")
    encrypted = encrypt_user_payload(owner_id, encoded)
    safe_call_id = hashlib.sha256(call_id.encode("utf-8")).hexdigest() if call_id else str(uuid4())
    with SyncSessionFactory() as session, session.begin():
        previous = session.scalar(
            select(PendingToolApproval)
            .where(
                PendingToolApproval.task_id == task_uuid,
                PendingToolApproval.tool_name == tool_name,
                PendingToolApproval.arguments_hash == digest,
            )
            .order_by(PendingToolApproval.updated_at.desc())
        )
        if previous:
            status = "INDETERMINATE" if previous.status == "RUNNING" else previous.status
            content = previous.result or ({"error": "execution_outcome_unknown"} if status == "INDETERMINATE" else {})
            return {"call_id": previous.call_id, "status": status, "content": content}
        row = session.scalar(
            select(PendingToolApproval).where(
                PendingToolApproval.task_id == task_uuid,
                PendingToolApproval.call_id == safe_call_id,
            )
        )
        if row:
            return {"call_id": row.call_id, "status": row.status, "content": row.result or {}}
        row = PendingToolApproval(
            id=uuid4(),
            task_id=task_uuid,
            owner_id=owner_id,
            call_id=safe_call_id,
            tool_name=tool_name[:200],
            connection_id=connection_id,
            remote_tool_name=remote_tool_name[:200],
            arguments=_redact_tool_arguments(arguments),
            arguments_hash=digest,
            encrypted_arguments=encrypted,
            status="PENDING_APPROVAL",
        )
        session.add(row)
        session.flush()
        return {"call_id": row.call_id, "status": row.status, "content": row.arguments}


async def list_tool_approvals(task_id: UUID, owner_id: UUID) -> list[PendingToolApproval] | None:
    async with AsyncSessionFactory() as session:
        owned = await session.scalar(
            select(TaskOwner.task_id).where(TaskOwner.task_id == task_id, TaskOwner.user_id == owner_id)
        )
        if not owned:
            return None
        return list(
            (await session.scalars(
                select(PendingToolApproval)
                .where(PendingToolApproval.task_id == task_id, PendingToolApproval.owner_id == owner_id)
                .order_by(PendingToolApproval.created_at)
            )).all()
        )


async def approve_tool_call(
    task_id: UUID, owner_id: UUID, call_id: str, approved: bool
) -> str | None:
    new_status = "APPROVED" if approved else "REJECTED"
    async with AsyncSessionFactory() as session, session.begin():
        task = await session.scalar(
            select(Task)
            .join(TaskOwner, TaskOwner.task_id == Task.id)
            .where(Task.id == task_id, TaskOwner.user_id == owner_id)
            .with_for_update()
        )
        if task is None:
            return None
        row = await session.scalar(
            select(PendingToolApproval)
            .where(
                PendingToolApproval.task_id == task_id,
                PendingToolApproval.owner_id == owner_id,
                PendingToolApproval.call_id == call_id,
            )
            .with_for_update()
        )
        if row is None:
            return None
        if row.status != "PENDING_APPROVAL" or task.status != "AWAITING_TOOL_APPROVAL":
            return "CONFLICT"
        row.status = new_status
        row.updated_at = datetime.now(UTC)
        if not approved:
            row.result = {"denied": True, "message": "The user declined this tool call."}
        task.status = "RESUMED"
        task.agent_logs = (task.agent_logs or []) + [
            {
                "agent": "HumanApproval",
                "action": f"{'Approved' if approved else 'Rejected'} tool call: {row.tool_name}",
                "timestamp": _stamp(),
            }
        ]
        session.add(
            DispatchOutbox(
                id=uuid4(),
                task_id=task_id,
                prompt=task.prompt,
                kind="tool_resume",
                approved=approved,
                call_id=row.call_id,
            )
        )
    return new_status


def execute_pending_tool_sync(task_id: str | UUID, call_id: str) -> dict[str, Any]:
    from src.agents.mcp_client import call_connection_tool_sync, decrypt_user_payload

    task_uuid = UUID(str(task_id))
    with SyncSessionFactory() as session, session.begin():
        row = session.scalar(
            select(PendingToolApproval)
            .where(PendingToolApproval.task_id == task_uuid, PendingToolApproval.call_id == call_id)
            .with_for_update()
        )
        if row is None:
            return {"status": "FAILED", "content": {"error": "approval_not_found"}}
        if row.status in {"SUCCEEDED", "FAILED", "REJECTED", "INDETERMINATE"}:
            return {"status": row.status, "content": row.result or {}}
        if row.status == "RUNNING":
            return {"status": "INDETERMINATE", "content": {"error": "execution_outcome_unknown"}}
        if row.status != "APPROVED":
            return {"status": "FAILED", "content": {"error": "approval_not_granted"}}
        row.status = "RUNNING"
        row.updated_at = datetime.now(UTC)
        user_id = row.owner_id
        connection_id = row.connection_id
        remote_name = row.remote_tool_name
        encrypted_args = row.encrypted_arguments
    try:
        if not connection_id or not encrypted_args or not remote_name:
            raise RuntimeError("approved_tool_configuration_missing")
        arguments = json.loads(decrypt_user_payload(user_id, encrypted_args))
        connection = get_connection_sync(user_id, connection_id)
        if connection is None:
            raise RuntimeError("approved_tool_connection_removed")
        result = call_connection_tool_sync(connection, user_id, remote_name, arguments)
        status = "FAILED" if result.get("is_error") else "SUCCEEDED"
        content = result
    except Exception as exc:
        # A timed-out side-effecting call may have completed remotely, so never retry it.
        status = "INDETERMINATE"
        content = {"error": type(exc).__name__, "message": "The tool outcome is unknown; Handoff will not retry it."}
    with SyncSessionFactory() as session, session.begin():
        row = session.scalar(
            select(PendingToolApproval).where(
                PendingToolApproval.task_id == task_uuid,
                PendingToolApproval.call_id == call_id,
            )
        )
        if row and row.status == "RUNNING":
            row.status = status
            row.result = content
            row.updated_at = datetime.now(UTC)
    return {"status": status, "content": content}


def get_connection_sync(user_id: UUID, connection_id: UUID) -> MCPConnection | None:
    with SyncSessionFactory() as session:
        return session.query(MCPConnection).filter_by(id=connection_id, user_id=user_id).one_or_none()


async def save_feedback(task_id: UUID, owner_id: UUID, rating: str, comment: str | None) -> None:
    async with AsyncSessionFactory() as session, session.begin():
        if not await session.scalar(
            select(TaskOwner.task_id).where(TaskOwner.task_id == task_id, TaskOwner.user_id == owner_id)
        ):
            return
        await session.execute(
            text("""INSERT INTO task_feedback(task_id,user_id,rating,comment)
            VALUES (:task_id,:user_id,:rating,:comment)
            ON CONFLICT(task_id,user_id) DO UPDATE SET rating=EXCLUDED.rating,
                comment=EXCLUDED.comment, updated_at=NOW()"""),
            {"task_id": task_id, "user_id": owner_id, "rating": rating, "comment": comment},
        )


def append_audit(task_id: str | UUID, agent: str, action: str) -> None:
    entry = {"agent": agent, "action": action[:2000], "timestamp": _stamp()}
    with SyncSessionFactory() as session, session.begin():
        session.execute(
            text(
                "UPDATE tasks SET agent_logs = COALESCE(agent_logs, '[]'::jsonb) || CAST(:entry AS jsonb) WHERE id = :task_id"
            ),
            {"entry": json.dumps([entry]), "task_id": str(task_id)},
        )


def set_task_status(
    task_id: str | UUID,
    status: str,
    *,
    result: str | None = None,
    audit: tuple[str, str] | None = None,
) -> None:
    uuid_value = UUID(str(task_id))
    values: dict[str, Any] = {"status": status}
    if result is not None:
        values["result"] = result
    with SyncSessionFactory() as session, session.begin():
        session.execute(update(Task).where(Task.id == uuid_value).values(**values))
        if audit:
            entry = {"agent": audit[0], "action": audit[1][:2000], "timestamp": _stamp()}
            session.execute(
                text(
                    "UPDATE tasks SET agent_logs = COALESCE(agent_logs, '[]'::jsonb) || CAST(:entry AS jsonb) WHERE id = :task_id"
                ),
                {"entry": json.dumps([entry]), "task_id": str(task_id)},
            )


def get_task_sync(task_id: str | UUID) -> dict[str, Any] | None:
    uuid_value = UUID(str(task_id))
    with SyncSessionFactory() as session:
        row = session.execute(select(Task).where(Task.id == uuid_value)).scalar_one_or_none()
        if row is None:
            return None
        return {
            "id": str(row.id),
            "prompt": row.prompt,
            "status": row.status,
            "result": row.result,
            "agent_logs": row.agent_logs or [],
        }


def persist_demo_task() -> None:
    demo_id = UUID("00000000-0000-4000-8000-000000000001")
    with SyncSessionFactory() as session, session.begin():
        if session.get(Task, demo_id):
            return
        session.add(
            Task(
                id=demo_id,
                prompt="Demo: compare LangGraph and CrewAI for a technical audience.",
                status="COMPLETED",
                result="LangGraph models workflows as explicit stateful graphs with checkpointing and resumable control flow. CrewAI organizes collaboration around role-defined agents, tasks, and crews. LangGraph is a strong fit when branching, durable state, and precise human approval gates matter; CrewAI is approachable for role-based teams and task delegation. Both require careful tool permissions, evaluation, and observability in production.",
                agent_logs=[
                    {
                        "agent": "ResearchAgent",
                        "action": "Collected comparison facts.",
                        "timestamp": _stamp(),
                    },
                    {
                        "agent": "WritingAgent",
                        "action": "Produced the demo summary.",
                        "timestamp": _stamp(),
                    },
                    {"agent": "System", "action": "Seeded demo task.", "timestamp": _stamp()},
                ],
            )
        )


def outbox_pending(limit: int = 50) -> list[dict[str, Any]]:
    with SyncSessionFactory() as session:
        rows = session.execute(
            select(DispatchOutbox)
            .where(
                DispatchOutbox.delivered_at.is_(None),
                (DispatchOutbox.claimed_at.is_(None))
                | (DispatchOutbox.claimed_at < func.now() - text("INTERVAL '30 seconds'")),
            )
            .order_by(DispatchOutbox.created_at)
            .limit(limit)
        ).scalars()
        return [
            {
                "id": row.id,
                "task_id": row.task_id,
                "prompt": row.prompt,
                "kind": row.kind,
                "approved": row.approved,
                "feedback": row.feedback,
                "call_id": row.call_id,
            }
            for row in rows
        ]


def mark_outbox_delivered(outbox_id: UUID) -> None:
    with SyncSessionFactory() as session, session.begin():
        session.execute(
            update(DispatchOutbox)
            .where(DispatchOutbox.id == outbox_id)
            .values(delivered_at=datetime.now(UTC))
        )


def claim_outbox(outbox_id: UUID) -> dict[str, Any] | None:
    with SyncSessionFactory() as session, session.begin():
        row = (
            session.execute(
                text("""UPDATE task_dispatch_outbox SET claimed_at=NOW()
                WHERE id=:id AND delivered_at IS NULL
                AND (claimed_at IS NULL OR claimed_at < NOW() - INTERVAL '30 seconds')
                RETURNING id, task_id, prompt, kind, approved, feedback, call_id"""),
                {"id": outbox_id},
            )
            .mappings()
            .one_or_none()
        )
        return dict(row) if row else None


def release_outbox(outbox_id: UUID) -> None:
    with SyncSessionFactory() as session, session.begin():
        session.execute(
            update(DispatchOutbox)
            .where(DispatchOutbox.id == outbox_id, DispatchOutbox.delivered_at.is_(None))
            .values(claimed_at=None)
        )
