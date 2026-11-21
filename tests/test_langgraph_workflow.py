from src.workflows import langgraph_workflow as workflow


def test_graph_pauses_at_approval_then_finishes_after_resume(monkeypatch) -> None:
    transitions = []
    state_store = {}
    monkeypatch.setattr(
        workflow.ResearchAgent, "run", lambda self, task_id, prompt: {"facts": ["research"]}
    )
    monkeypatch.setattr(
        workflow.WritingAgent,
        "run",
        lambda self, task_id, prompt: "A useful draft with clear tradeoffs.",
    )
    monkeypatch.setattr(
        workflow,
        "transition",
        lambda task_id, status, **kwargs: transitions.append((status, kwargs)),
    )
    monkeypatch.setattr(
        workflow, "save_graph_state", lambda task_id, value: state_store.update(value)
    )
    monkeypatch.setattr(workflow, "workspace_key", lambda task_id: f"task:{task_id}:workspace")

    workflow.run_langgraph_phase("task-123", "compare frameworks")
    assert transitions[-1][0] == "AWAITING_APPROVAL"
    assert state_store["draft"] == "A useful draft with clear tradeoffs."
    assert state_store["findings_key"] == "task:task-123:workspace"

    monkeypatch.setattr(workflow, "read_graph_state", lambda task_id: None, raising=False)
    monkeypatch.setattr("src.agents.scratchpad.read_graph_state", lambda task_id: dict(state_store))
    monkeypatch.setattr(
        workflow,
        "transition",
        lambda task_id, status, **kwargs: transitions.append((status, kwargs)),
    )
    workflow.resume_langgraph_phase("task-123", True, "Looks good")
    assert transitions[-1][0] == "COMPLETED"
    assert "Human review note: Looks good" in transitions[-1][1]["result"]
