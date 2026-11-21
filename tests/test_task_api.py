import time
from uuid import uuid4

from src.db.models import Task


def test_create_task_returns_202_quickly_and_dispatches_after_response(client, monkeypatch) -> None:
    import src.api.tasks as routes

    task_id = uuid4()
    monkeypatch.setattr(routes, "enforce_submission_limit", lambda request: _resolved())
    monkeypatch.setattr(routes, "persist_task", lambda prompt: _resolved(_task(task_id, prompt)))
    monkeypatch.setattr(routes, "set_engine", lambda task_id, engine: None)
    dispatched = []
    monkeypatch.setattr(routes, "deliver_for_task", lambda value: dispatched.append(value))
    start = time.perf_counter()
    response = client.post("/api/v1/tasks", json={"prompt": "Compare LangGraph and CrewAI."})
    elapsed = time.perf_counter() - start
    assert response.status_code == 202
    assert response.json() == {"task_id": str(task_id), "status": "PENDING"}
    assert elapsed < 0.5
    assert dispatched == [task_id]


def test_create_task_validates_blank_and_long_prompts(client) -> None:
    assert client.post("/api/v1/tasks", json={"prompt": " "}).status_code == 422
    assert client.post("/api/v1/tasks", json={"prompt": "x" * 4001}).status_code == 422


def test_get_task_returns_contract_and_unknown_is_404(client, monkeypatch) -> None:
    import src.api.tasks as routes

    task_id = uuid4()
    row = _task(task_id, "Compare the frameworks.")
    row.status = "AWAITING_APPROVAL"
    row.result = "A draft."
    row.agent_logs = [
        {
            "agent": "ResearchAgent",
            "action": "Collected facts.",
            "timestamp": "2026-11-21T10:00:00.000Z",
        }
    ]
    monkeypatch.setattr(
        routes, "get_task", lambda value: _resolved(row if value == task_id else None)
    )
    response = client.get(f"/api/v1/tasks/{task_id}")
    assert response.status_code == 200
    assert response.json()["agent_logs"][0]["agent"] == "ResearchAgent"
    assert response.json()["result"] == "A draft."
    missing = client.get(f"/api/v1/tasks/{uuid4()}")
    assert missing.status_code == 404
    assert "error" in missing.json()


def test_malformed_uuid_is_422(client) -> None:
    response = client.get("/api/v1/tasks/not-a-uuid")
    assert response.status_code == 422


def _task(task_id, prompt):
    return Task(
        id=task_id,
        prompt=prompt,
        status="PENDING",
        result=None,
        agent_logs=[],
        created_at=__import__("datetime").datetime.now(__import__("datetime").UTC),
        updated_at=__import__("datetime").datetime.now(__import__("datetime").UTC),
    )


async def _resolved(value=None):
    return value
