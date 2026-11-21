from uuid import uuid4


def test_approval_requires_waiting_state_and_dispatches_resume(client, monkeypatch) -> None:
    import src.api.approvals as routes

    task_id = uuid4()
    monkeypatch.setattr(routes, "approve_task", _async_result("RESUMED"))
    monkeypatch.setattr(routes, "publish_status_async", _async_result(None))
    dispatched = []
    monkeypatch.setattr(routes, "deliver_for_task", lambda value: dispatched.append(value))
    response = client.post(
        f"/api/v1/tasks/{task_id}/approve", json={"approved": True, "feedback": "Proceed"}
    )
    assert response.status_code == 200
    assert response.json() == {"task_id": str(task_id), "status": "RESUMED"}
    assert dispatched == [task_id]


def test_approval_conflict_and_missing_task(client, monkeypatch) -> None:
    import src.api.approvals as routes

    task_id = uuid4()
    monkeypatch.setattr(routes, "approve_task", _async_result("CONFLICT"))
    assert (
        client.post(f"/api/v1/tasks/{task_id}/approve", json={"approved": True}).status_code == 409
    )
    monkeypatch.setattr(routes, "approve_task", _async_result(None))
    assert (
        client.post(f"/api/v1/tasks/{task_id}/approve", json={"approved": True}).status_code == 404
    )


def test_rejection_is_a_terminal_decision_and_is_sent_to_engine(client, monkeypatch) -> None:
    import src.api.approvals as routes

    task_id = uuid4()
    monkeypatch.setattr(routes, "approve_task", _async_result("REJECTED"))
    monkeypatch.setattr(routes, "publish_status_async", _async_result(None))
    dispatched = []
    monkeypatch.setattr(routes, "deliver_for_task", lambda value: dispatched.append(value))
    response = client.post(
        f"/api/v1/tasks/{task_id}/approve", json={"approved": False, "feedback": "Revise"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "REJECTED"
    assert dispatched == [task_id]


def _async_result(result):
    async def value(*args, **kwargs):
        return result

    return value
