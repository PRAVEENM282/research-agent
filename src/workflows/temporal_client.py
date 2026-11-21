import asyncio

from temporalio.client import Client

from src.config.settings import settings
from src.workflows.temporal_workflow import HandoffWorkflow

TASK_QUEUE = "handoff-tasks"


async def _client() -> Client:
    kwargs = {"namespace": settings.temporal_namespace}
    if settings.temporal_api_key:
        kwargs["api_key"] = settings.temporal_api_key
        kwargs["tls"] = True
    return await Client.connect(settings.temporal_address, **kwargs)


async def _start_workflow(task_id: str, prompt: str) -> None:
    client = await _client()
    try:
        await client.start_workflow(
            HandoffWorkflow.run,
            args=[task_id, prompt],
            id=task_id,
            task_queue=TASK_QUEUE,
        )
    except Exception as exc:
        if "already started" not in str(exc).lower() and "already exists" not in str(exc).lower():
            raise


async def _signal_approval(task_id: str, approved: bool, feedback: str) -> None:
    client = await _client()
    handle = client.get_workflow_handle(task_id)
    await handle.signal(HandoffWorkflow.approve, args=[approved, feedback])


async def _signal_tool_approval(task_id: str, call_id: str, approved: bool) -> None:
    client = await _client()
    handle = client.get_workflow_handle(task_id)
    await handle.signal(HandoffWorkflow.approve_tool, args=[call_id, approved])


def start_workflow(task_id: str, prompt: str) -> None:
    asyncio.run(_start_workflow(task_id, prompt))


def signal_approval(task_id: str, approved: bool, feedback: str) -> None:
    asyncio.run(_signal_approval(task_id, approved, feedback))


def signal_tool_approval(task_id: str, call_id: str, approved: bool) -> None:
    asyncio.run(_signal_tool_approval(task_id, call_id, approved))
