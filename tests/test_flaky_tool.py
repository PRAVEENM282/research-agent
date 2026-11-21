from collections import defaultdict

from src.agents import research_agent, tools


def test_every_flaky_task_fails_once_then_logs_retry_and_success(monkeypatch) -> None:
    counters = defaultdict(int)
    activities: list[tuple[str, str]] = []
    monkeypatch.setattr(
        tools, "increment_tool_attempt", lambda task_id, query: _increment(counters, task_id, query)
    )
    monkeypatch.setattr(
        tools,
        "activity_log",
        lambda task_id, agent, action, **kwargs: activities.append((task_id, action)),
    )
    monkeypatch.setattr(
        research_agent,
        "activity_log",
        lambda task_id, agent, action, **kwargs: activities.append((task_id, action)),
    )
    monkeypatch.setattr(research_agent, "append_audit", lambda *args: None)
    monkeypatch.setattr(research_agent, "write_workspace", lambda *args: None)

    agent = research_agent.ResearchAgent()
    for task_id in ("task-a", "task-b"):
        findings = agent.run(task_id, "Please include __FLAKY_TEST__")
        assert findings["query"] == "__FLAKY_TEST__"
        assert counters[(task_id, "__FLAKY_TEST__")] == 2
        actions = [action for current_task, action in activities if current_task == task_id]
        assert actions.index("Tool failed: Simulated transient network timeout.") < actions.index(
            "Retrying tool call, attempt 2"
        )
        assert actions.index("Retrying tool call, attempt 2") < actions.index(
            "Tool succeeded: simulated_search_tool"
        )


def _increment(counter, task_id, query):
    key = (task_id, query)
    counter[key] += 1
    return counter[key]
