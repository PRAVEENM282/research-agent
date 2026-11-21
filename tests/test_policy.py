import pytest
from src.agents.policy import validate_prompt, validate_tool_name


def test_prompt_is_bounded_and_trimmed() -> None:
    assert validate_prompt("  research this  ") == "research this"
    with pytest.raises(ValueError):
        validate_prompt(" " * 5)
    with pytest.raises(ValueError):
        validate_prompt("x" * 4001)


def test_agent_tools_are_allowlisted() -> None:
    validate_tool_name("simulated_search_tool")
    with pytest.raises(PermissionError):
        validate_tool_name("shell")
