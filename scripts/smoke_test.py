import asyncio
import json
import logging
import os
from collections import Counter

import httpx
import websockets

API = os.getenv("SMOKE_API_URL", "http://127.0.0.1:8000").rstrip("/")
WS = API.replace("https://", "wss://").replace("http://", "ws://")
log = logging.getLogger("handoff.smoke")


async def exercise_flaky_task(index: int) -> None:
    prompt = f"Verify simulated search recovery run {index} with __FLAKY_TEST__ and summarize the result."
    async with httpx.AsyncClient(base_url=API, timeout=8) as client:
        response = await client.post("/api/v1/tasks", json={"prompt": prompt})
        response.raise_for_status()
        task_id = response.json()["task_id"]
        observed: list[str] = []
        deadline = asyncio.get_running_loop().time() + 100
        async with websockets.connect(
            f"{WS}/ws/tasks/{task_id}", open_timeout=8, close_timeout=3
        ) as socket:
            while "AWAITING_APPROVAL" not in observed:
                remaining = deadline - asyncio.get_running_loop().time()
                if remaining <= 0:
                    raise TimeoutError(f"Task {task_id} did not reach approval.")
                event = await asyncio.wait_for(socket.recv(), timeout=remaining)
                payload = json.loads(event)
                observed.append(payload["status"])
                if payload["status"] == "FAILED":
                    raise RuntimeError(f"Task {task_id} failed before approval.")
            workspace = await client.get(f"/api/v1/tasks/{task_id}/workspace")
            workspace.raise_for_status()
            if workspace.json()["workspace"]["query"] != "__FLAKY_TEST__":
                raise AssertionError("The flaky task did not use the exact query.")
            approval = await client.post(
                f"/api/v1/tasks/{task_id}/approve",
                json={"approved": True, "feedback": "Smoke check approved."},
            )
            approval.raise_for_status()
            if approval.json()["status"] != "RESUMED":
                raise AssertionError("Approval did not resume the workflow.")
            while "COMPLETED" not in observed:
                remaining = deadline - asyncio.get_running_loop().time()
                if remaining <= 0:
                    raise TimeoutError(f"Task {task_id} did not complete.")
                event = await asyncio.wait_for(socket.recv(), timeout=remaining)
                payload = json.loads(event)
                observed.append(payload["status"])
        task = (await client.get(f"/api/v1/tasks/{task_id}")).json()
        if task["status"] != "COMPLETED" or "second attempt" not in (task["result"] or ""):
            raise AssertionError("The flaky task did not complete with its retry result.")
        activity = (await client.get(f"/api/v1/tasks/{task_id}/activity")).json()["entries"]
        actions = [entry["action_details"] for entry in activity]
        markers = [
            "Tool failed: Simulated transient network timeout.",
            "Retrying tool call, attempt 2",
            "Tool succeeded: simulated_search_tool",
        ]
        positions = [
            next((i for i, action in enumerate(actions) if marker in action), -1)
            for marker in markers
        ]
        if any(position < 0 for position in positions) or positions != sorted(positions):
            raise AssertionError(f"Required retry log order is missing: {positions}")
        agents = {entry["agent"] for entry in task["agent_logs"]}
        if not {"ResearchAgent", "WritingAgent", "HumanApproval", "System"}.issubset(agents):
            raise AssertionError("The task audit trail is incomplete.")
        unique_statuses = set(observed)
        if (
            len(unique_statuses) < 3
            or "AWAITING_APPROVAL" not in unique_statuses
            or "COMPLETED" not in unique_statuses
        ):
            raise AssertionError(f"The WebSocket lifecycle was incomplete: {observed}")
        log.info("Flaky lifecycle %s passed with events %s", task_id, Counter(observed))


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    async with httpx.AsyncClient(base_url=API, timeout=5) as client:
        for _ in range(30):
            try:
                if (await client.get("/health")).status_code == 200:
                    break
            except httpx.HTTPError:
                await asyncio.sleep(1)
            else:
                await asyncio.sleep(1)
        else:
            raise RuntimeError(f"Handoff API did not become healthy at {API}.")
    await exercise_flaky_task(1)
    await exercise_flaky_task(2)


if __name__ == "__main__":
    asyncio.run(main())
