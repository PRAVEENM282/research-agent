import json
import logging

from src.config.logging_config import configure_logging


def test_activity_log_is_json_with_required_millisecond_utc_fields(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LOG_DIR", str(tmp_path))
    configure_logging("INFO")
    logging.getLogger("test.activity").info(
        "Research completed",
        extra={
            "task_id": "abc",
            "agent_name": "ResearchAgent",
            "action_details": "Research completed",
        },
    )
    for handler in logging.getLogger().handlers:
        handler.flush()
    entry = json.loads(
        (tmp_path / "agent_activity.log").read_text(encoding="utf-8").splitlines()[-1]
    )
    assert {"timestamp", "task_id", "agent_name", "action_details"} <= entry.keys()
    assert entry["agent_name"] == "ResearchAgent"
    assert entry["timestamp"].endswith("Z")
    assert len(entry["timestamp"].split(".")[-1].removesuffix("Z")) == 3
