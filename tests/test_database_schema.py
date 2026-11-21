from src.db.models import Task


def test_tasks_table_has_the_exact_seven_column_contract() -> None:
    assert list(Task.__table__.columns.keys()) == [
        "id",
        "prompt",
        "status",
        "result",
        "agent_logs",
        "created_at",
        "updated_at",
    ]
    assert str(Task.__table__.c.id.type) == "UUID"
    assert str(Task.__table__.c.prompt.type) == "TEXT"
    assert str(Task.__table__.c.status.type) == "VARCHAR(50)"
    assert str(Task.__table__.c.result.type) == "TEXT"
    assert str(Task.__table__.c.agent_logs.type) == "JSONB"


def test_schema_bootstrap_uses_idempotent_table_creation() -> None:
    from pathlib import Path

    sql = Path("src/db/init.sql").read_text(encoding="utf-8")
    assert "CREATE TABLE IF NOT EXISTS tasks" in sql
    assert "CREATE INDEX IF NOT EXISTS ix_tasks_created_at_desc" in sql
    assert "CREATE INDEX IF NOT EXISTS ix_tasks_status" in sql
    assert "CREATE TRIGGER tasks_updated_at_trigger" in sql
