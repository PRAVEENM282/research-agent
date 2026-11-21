from src.worker import tasks


def test_temporal_engine_uses_temporal_start(monkeypatch) -> None:
    started = []
    monkeypatch.setattr(tasks, "get_task_sync", lambda task_id: {"status": "PENDING"})
    monkeypatch.setattr(tasks, "get_engine", lambda task_id: "temporal")
    monkeypatch.setattr(tasks, "set_engine", lambda *args: None)
    monkeypatch.setattr(tasks, "activity_log", lambda *args: None)
    monkeypatch.setattr(
        "src.workflows.temporal_client.start_workflow",
        lambda *args: started.append(args),
        raising=False,
    )
    tasks.run_agent_workflow.run("task-a", "prompt")
    assert started == [("task-a", "prompt")]


def test_celery_langgraph_engine_runs_graph_path(monkeypatch) -> None:
    phases = []

    class LockRedis:
        def set(self, *args, **kwargs):
            return True

        def eval(self, *args):
            return 1

    monkeypatch.setattr(tasks, "get_task_sync", lambda task_id: {"status": "PENDING"})
    monkeypatch.setattr(tasks, "get_engine", lambda task_id: "celery_langgraph")
    monkeypatch.setattr(tasks, "set_engine", lambda *args: None)
    monkeypatch.setattr(tasks, "redis_client", lambda: LockRedis())
    monkeypatch.setattr(tasks, "activity_log", lambda *args: None)
    monkeypatch.setattr(
        tasks, "run_langgraph_phase", lambda task_id, prompt: phases.append((task_id, prompt))
    )
    tasks.run_agent_workflow.run("task-b", "prompt")
    assert phases == [("task-b", "prompt")]
