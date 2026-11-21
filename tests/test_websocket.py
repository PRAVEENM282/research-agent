import json
from types import SimpleNamespace
from uuid import uuid4

from src.db.models import Task


def test_websocket_sends_current_status_then_events_and_closes(client, monkeypatch) -> None:
    import src.api.websocket as socket_route

    task_id = uuid4()
    row = Task(
        id=task_id,
        prompt="test prompt",
        status="PENDING",
        result=None,
        agent_logs=[],
    )

    class FakeSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def get(self, model, value):
            return row if value == task_id else None

    class FakePubsub:
        def __init__(self):
            self.events = iter(
                [
                    {"data": json.dumps({"task_id": str(task_id), "status": state})}
                    for state in ["RUNNING", "AWAITING_APPROVAL", "RESUMED", "COMPLETED"]
                ]
            )

        async def subscribe(self, channel):
            return None

        async def get_message(self, **kwargs):
            try:
                return next(self.events)
            except StopIteration:
                return None

        async def unsubscribe(self, channel):
            return None

        async def aclose(self):
            return None

    class FakeRedis:
        def pubsub(self):
            return FakePubsub()

        async def aclose(self):
            return None

    monkeypatch.setattr(socket_route, "AsyncSessionFactory", FakeSession)
    monkeypatch.setattr(
        socket_route, "Redis", SimpleNamespace(from_url=lambda *args, **kwargs: FakeRedis())
    )
    with client.websocket_connect(f"/ws/tasks/{task_id}") as websocket:
        statuses = [websocket.receive_json()["status"] for _ in range(5)]
    assert statuses == ["PENDING", "RUNNING", "AWAITING_APPROVAL", "RESUMED", "COMPLETED"]
