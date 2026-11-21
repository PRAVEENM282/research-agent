from src.config.logging_config import activity_log
from src.db.repository import append_audit


def record(task_id: str, agent: str, action: str) -> None:
    append_audit(task_id, agent, action)
    activity_log(task_id, agent, action)
