from src.workflows import temporal_client


async def test_temporal_client_passes_multiple_workflow_and_signal_arguments(monkeypatch) -> None:
    calls = []

    class Handle:
        async def signal(self, signal, *, args):
            calls.append(("signal", signal, args))

    class Client:
        async def start_workflow(self, workflow, *, args, id, task_queue):
            calls.append(("start", workflow, args, id, task_queue))

        def get_workflow_handle(self, workflow_id):
            calls.append(("handle", workflow_id))
            return Handle()

    async def client():
        return Client()

    monkeypatch.setattr(temporal_client, "_client", client)

    await temporal_client._start_workflow("task-1", "write a summary")
    await temporal_client._signal_approval("task-1", True, "keep the first section")

    assert calls == [
        (
            "start",
            temporal_client.HandoffWorkflow.run,
            ["task-1", "write a summary"],
            "task-1",
            "handoff-tasks",
        ),
        ("handle", "task-1"),
        ("signal", temporal_client.HandoffWorkflow.approve, [True, "keep the first section"]),
    ]
