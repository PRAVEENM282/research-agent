import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor

from temporalio.client import Client
from temporalio.worker import Worker

from src.config.logging_config import configure_logging
from src.config.settings import settings
from src.workflows.temporal_activities import (
    await_approval,
    await_tool_approval,
    finalize,
    mark_running,
    reject,
    research,
    resolve_tool_approval,
    workflow_failed,
    write_draft,
)
from src.workflows.temporal_client import TASK_QUEUE
from src.workflows.temporal_workflow import HandoffWorkflow

logger = logging.getLogger(__name__)


async def run() -> None:
    configure_logging(settings.log_level)
    kwargs = {"namespace": settings.temporal_namespace}
    if settings.temporal_api_key:
        kwargs["api_key"] = settings.temporal_api_key
        kwargs["tls"] = True
    client = await Client.connect(settings.temporal_address, **kwargs)
    executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="handoff-activity")
    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[HandoffWorkflow],
        activities=[
            mark_running,
            research,
            write_draft,
            await_approval,
            await_tool_approval,
            resolve_tool_approval,
            finalize,
            reject,
            workflow_failed,
        ],
        activity_executor=executor,
        max_concurrent_activities=4,
    )
    logger.info(
        "Temporal worker is ready",
        extra={"task_id": "", "agent_name": "System", "action_details": "Temporal worker ready"},
    )
    try:
        await worker.run()
    finally:
        executor.shutdown(wait=True, cancel_futures=True)


if __name__ == "__main__":
    asyncio.run(run())
