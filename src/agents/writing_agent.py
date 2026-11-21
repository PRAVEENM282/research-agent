import time

from src.agents.llm import generate_draft
from src.agents.policy import validate_draft
from src.agents.scratchpad import read_workspace
from src.config.logging_config import activity_log
from src.db.repository import append_audit


class WritingAgent:
    def run(self, task_id: str, prompt: str) -> str:
        activity_log(task_id, "WritingAgent", "Writing started")
        append_audit(task_id, "WritingAgent", "Started draft writing from Redis scratchpad.")
        workspace = read_workspace(task_id)
        if not workspace:
            raise RuntimeError("Research workspace was unavailable to WritingAgent.")
        draft = validate_draft(generate_draft(task_id, prompt, workspace))
        activity_log(task_id, "WritingAgent", "Draft completed and ready for human review")
        append_audit(task_id, "WritingAgent", "Completed draft from shared Redis findings.")
        time.sleep(0.8)
        return draft
