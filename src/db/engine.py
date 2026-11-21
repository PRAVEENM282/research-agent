import asyncio
import logging

from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.config.settings import settings
from src.db.migrations import run_schema_migrations

logger = logging.getLogger(__name__)

async_engine = create_async_engine(
    settings.async_database_url, pool_pre_ping=True, pool_size=5, max_overflow=10
)
AsyncSessionFactory = async_sessionmaker(async_engine, expire_on_commit=False, class_=AsyncSession)
sync_engine = create_engine(
    settings.sync_database_url, pool_pre_ping=True, pool_size=5, max_overflow=10
)
SyncSessionFactory = sessionmaker(sync_engine, expire_on_commit=False)


def init_db_sync() -> None:
    with sync_engine.begin() as connection:
        connection.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS pgcrypto")
        connection.exec_driver_sql(
            """CREATE TABLE IF NOT EXISTS tasks (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(), prompt TEXT NOT NULL,
                status VARCHAR(50) NOT NULL, result TEXT NULL, agent_logs JSONB NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )"""
        )
        connection.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS ix_tasks_created_at_desc ON tasks (created_at DESC)"
        )
        connection.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_tasks_status ON tasks (status)")
        connection.exec_driver_sql(
            """CREATE OR REPLACE FUNCTION handoff_set_updated_at() RETURNS TRIGGER AS $$
               BEGIN NEW.updated_at = NOW(); RETURN NEW; END; $$ LANGUAGE plpgsql"""
        )
        connection.exec_driver_sql("DROP TRIGGER IF EXISTS tasks_updated_at_trigger ON tasks")
        connection.exec_driver_sql(
            "CREATE TRIGGER tasks_updated_at_trigger BEFORE UPDATE ON tasks "
            "FOR EACH ROW EXECUTE FUNCTION handoff_set_updated_at()"
        )
        connection.exec_driver_sql(
            """CREATE TABLE IF NOT EXISTS task_dispatch_outbox (
                id UUID PRIMARY KEY, task_id UUID NOT NULL, prompt TEXT NOT NULL,
                kind VARCHAR(20) NOT NULL DEFAULT 'run', approved BOOLEAN NULL, feedback TEXT NULL,
                call_id VARCHAR(200) NULL,
                delivered_at TIMESTAMPTZ NULL, claimed_at TIMESTAMPTZ NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )"""
        )
        connection.exec_driver_sql(
            "ALTER TABLE task_dispatch_outbox ADD COLUMN IF NOT EXISTS claimed_at TIMESTAMPTZ NULL"
        )
        connection.exec_driver_sql(
            "ALTER TABLE task_dispatch_outbox ADD COLUMN IF NOT EXISTS call_id VARCHAR(200) NULL"
        )
        connection.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS ix_task_dispatch_pending ON task_dispatch_outbox (created_at) WHERE delivered_at IS NULL"
        )
        run_schema_migrations(connection)
    logger.info(
        "Database schema initialized",
        extra={
            "task_id": "",
            "agent_name": "System",
            "action_details": "Database schema initialized",
        },
    )


async def init_db() -> None:
    await asyncio.to_thread(init_db_sync)


async def close_engines() -> None:
    await async_engine.dispose()
    await asyncio.to_thread(sync_engine.dispose)


async def database_ping() -> bool:
    try:
        async with async_engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def database_ping_sync() -> bool:
    try:
        with sync_engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
