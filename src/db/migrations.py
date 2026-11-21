import logging

from sqlalchemy import text
from sqlalchemy.engine import Connection

from src.db.models import Base

logger = logging.getLogger(__name__)


def run_schema_migrations(connection: Connection) -> None:
    """Create additive tables; keep legacy tasks private until an owner signs in."""
    Base.metadata.create_all(connection)
    connection.exec_driver_sql(
        "ALTER TABLE pending_tool_approvals ADD COLUMN IF NOT EXISTS arguments_hash VARCHAR(64) NOT NULL DEFAULT ''"
    )
    connection.exec_driver_sql(
        "ALTER TABLE pending_tool_approvals ADD COLUMN IF NOT EXISTS encrypted_arguments BYTEA NULL"
    )
    connection.exec_driver_sql(
        "ALTER TABLE pending_tool_approvals ADD COLUMN IF NOT EXISTS connection_id UUID NULL REFERENCES mcp_connections(id) ON DELETE SET NULL"
    )
    connection.exec_driver_sql(
        "ALTER TABLE pending_tool_approvals ADD COLUMN IF NOT EXISTS remote_tool_name VARCHAR(200) NULL"
    )
    connection.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS ix_pending_tool_approvals_task_hash ON pending_tool_approvals(task_id, arguments_hash)"
    )
    connection.exec_driver_sql(
        """CREATE TABLE IF NOT EXISTS handoff_schema_migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )"""
    )
    connection.exec_driver_sql(
        "INSERT INTO handoff_schema_migrations(version) VALUES (1) ON CONFLICT (version) DO NOTHING"
    )
    connection.exec_driver_sql(
        "INSERT INTO handoff_schema_migrations(version) VALUES (2) ON CONFLICT (version) DO NOTHING"
    )

    unowned_count = connection.exec_driver_sql(
        """SELECT COUNT(*) FROM tasks t LEFT JOIN task_owners o ON o.task_id=t.id
        WHERE o.task_id IS NULL"""
    ).scalar_one()
    if unowned_count:
        logger.warning(
            "%s legacy tasks remain hidden until the allowlisted bootstrap email completes OIDC sign-in",
            unowned_count,
        )
