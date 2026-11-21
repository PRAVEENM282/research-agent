import logging
import traceback

import redis
from celery import shared_task
from sqlalchemy.exc import OperationalError

from src.agents.scratchpad import get_engine, redis_client, set_engine
from src.config.logging_config import activity_log
from src.config.settings import settings
from src.db.repository import get_task_sync
from src.workflows.langgraph_workflow import resume_langgraph_phase, run_langgraph_phase
from src.workflows.services import fail_task

logger = logging.getLogger(__name__)
INFRA_ERRORS = (OperationalError, redis.exceptions.RedisError, OSError, TimeoutError)


def _traceback_frames(exc: Exception) -> str:
    return "".join(traceback.format_tb(exc.__traceback__))[-6000:]


def _release_lock(key: str, token: str) -> None:
    redis_client().eval(
        "if redis.call('GET', KEYS[1]) == ARGV[1] then return redis.call('DEL', KEYS[1]) else return 0 end",
        1,
        key,
        token,
    )


@shared_task(
    bind=True,
    name="src.worker.tasks.run_agent_workflow",
    acks_late=True,
    reject_on_worker_lost=True,
    autoretry_for=INFRA_ERRORS,
    retry_backoff=True,
    retry_backoff_max=30,
    retry_jitter=True,
    max_retries=3,
)
def run_agent_workflow(self, task_id: str, prompt: str) -> None:
    task = get_task_sync(task_id)
    if not task or task["status"] not in {"PENDING", "RUNNING"}:
        return
    engine = get_engine(task_id) or settings.workflow_engine
    set_engine(task_id, engine)
    activity_log(task_id, "System", f"Dispatching workflow engine: {engine}")
    try:
        if engine == "temporal":
            from src.workflows.temporal_client import start_workflow

            start_workflow(task_id, prompt)
        else:
            key = f"task:{task_id}:phase-run-lock"
            token = self.request.id or "worker"
            client = redis_client()
            if not client.set(key, token, nx=True, ex=300):
                return
            try:
                run_langgraph_phase(task_id, prompt)
            finally:
                _release_lock(key, token)
    except INFRA_ERRORS:
        raise
    except Exception as exc:
        logger.error(
            "Workflow dispatch failed (%s)\n%s",
            type(exc).__name__,
            _traceback_frames(exc),
            extra={
                "task_id": task_id,
                "agent_name": "System",
                "action_details": "Workflow dispatch failed",
            },
        )
        fail_task(
            task_id,
            "Workflow failed. Check provider credentials and service health, then create a new task.",
        )


@shared_task(
    bind=True,
    name="src.worker.tasks.resume_agent_workflow",
    acks_late=True,
    reject_on_worker_lost=True,
    autoretry_for=INFRA_ERRORS,
    retry_backoff=True,
    retry_backoff_max=30,
    retry_jitter=True,
    max_retries=3,
)
def resume_agent_workflow(self, task_id: str, approved: bool, feedback: str) -> None:
    task = get_task_sync(task_id)
    if not task or task["status"] not in {"RESUMED", "REJECTED"}:
        return
    engine = get_engine(task_id) or settings.workflow_engine
    activity_log(task_id, "System", f"Resuming workflow engine: {engine}")
    try:
        if engine == "temporal":
            from src.workflows.temporal_client import signal_approval

            signal_approval(task_id, approved, feedback)
        else:
            key = f"task:{task_id}:phase-resume-lock"
            token = self.request.id or "worker"
            client = redis_client()
            if not client.set(key, token, nx=True, ex=300):
                return
            try:
                resume_langgraph_phase(task_id, approved, feedback)
            finally:
                _release_lock(key, token)
    except INFRA_ERRORS:
        raise
    except Exception as exc:
        logger.error(
            "Workflow resume failed (%s)\n%s",
            type(exc).__name__,
            _traceback_frames(exc),
            extra={
                "task_id": task_id,
                "agent_name": "System",
                "action_details": "Workflow resume failed",
            },
        )
        fail_task(
            task_id, "Workflow could not resume. Check workflow service health and task state."
        )


@shared_task(
    bind=True,
    name="src.worker.tasks.resume_tool_workflow",
    acks_late=True,
    reject_on_worker_lost=True,
    autoretry_for=INFRA_ERRORS,
    retry_backoff=True,
    retry_backoff_max=30,
    retry_jitter=True,
    max_retries=3,
)
def resume_tool_workflow(self, task_id: str, call_id: str, approved: bool) -> None:
    task = get_task_sync(task_id)
    if not task or task["status"] != "RESUMED":
        return
    engine = get_engine(task_id) or settings.workflow_engine
    try:
        if engine == "temporal":
            from src.workflows.temporal_client import signal_tool_approval

            signal_tool_approval(task_id, call_id, approved)
        else:
            key = f"task:{task_id}:tool-resume-lock"
            token = self.request.id or "worker"
            client = redis_client()
            if not client.set(key, token, nx=True, ex=300):
                return
            try:
                from src.workflows.langgraph_workflow import resume_langgraph_tool_approval

                resume_langgraph_tool_approval(task_id, call_id, approved)
            finally:
                _release_lock(key, token)
    except INFRA_ERRORS:
        raise
    except Exception as exc:
        logger.error(
            "Tool approval resume failed (%s)\n%s",
            type(exc).__name__,
            _traceback_frames(exc),
            extra={"task_id": task_id, "agent_name": "System", "action_details": "Tool approval resume failed"},
        )
        fail_task(task_id, "The workflow could not resume after tool approval. Check the task audit.")


@shared_task(name="src.worker.tasks.dispatch_pending_outbox", ignore_result=True)
def dispatch_pending_outbox() -> int:
    from src.worker.dispatch import drain_outbox

    try:
        return drain_outbox()
    except INFRA_ERRORS as exc:
        logger.error(
            "Outbox scan failed (%s)\n%s",
            type(exc).__name__,
            _traceback_frames(exc),
            extra={"task_id": "", "agent_name": "System", "action_details": "Outbox scan failed"},
        )
        return 0
