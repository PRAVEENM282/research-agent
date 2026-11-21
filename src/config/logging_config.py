import logging
import os
from datetime import UTC, datetime
from pathlib import Path

from concurrent_log_handler import ConcurrentRotatingFileHandler
from pythonjsonlogger.json import JsonFormatter


class HandoffJsonFormatter(JsonFormatter):
    def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:
        return (
            datetime.fromtimestamp(record.created, UTC)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z")
        )


class RequiredFields(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        for key in ("task_id", "agent_name", "action_details"):
            if not hasattr(record, key):
                setattr(record, key, "system" if key == "agent_name" else "")
        return True


def configure_logging(level: str = "INFO") -> None:
    log_dir = Path(os.getenv("LOG_DIR", "logs"))
    log_dir.mkdir(parents=True, exist_ok=True)
    formatter = HandoffJsonFormatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s %(task_id)s %(agent_name)s %(action_details)s",
        rename_fields={"asctime": "timestamp"},
    )
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    root.handlers.clear()
    for handler in (
        logging.StreamHandler(),
        ConcurrentRotatingFileHandler(
            log_dir / "agent_activity.log",
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        ),
    ):
        handler.setFormatter(formatter)
        handler.addFilter(RequiredFields())
        root.addHandler(handler)


def activity_log(
    task_id: str, agent_name: str, action_details: str, *, level: int = logging.INFO
) -> None:
    logging.getLogger("handoff.activity").log(
        level,
        action_details,
        extra={"task_id": str(task_id), "agent_name": agent_name, "action_details": action_details},
    )
