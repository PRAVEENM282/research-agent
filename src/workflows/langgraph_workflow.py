from typing import Any

from langgraph.graph import END, START, StateGraph

from src.agents.research_agent import ResearchAgent
from src.agents.scratchpad import save_graph_state, workspace_key
from src.agents.state import AgentState
from src.agents.writing_agent import WritingAgent
from src.db.repository import execute_pending_tool_sync
from src.workflows.services import transition


def _research(state: AgentState) -> dict[str, Any]:
    if state.get("findings_key") and not state.get("resume_tool"):
        return {}
    findings = ResearchAgent().run(state["task_id"], state["prompt"])
    return {
        "findings": findings,
        "findings_key": workspace_key(state["task_id"]),
        "pending_approval": findings.get("pending_approval"),
        "resume_tool": False,
    }


def _tool_approval_gate(state: AgentState) -> dict[str, Any]:
    pending = state.get("pending_approval") or {}
    transition(
        state["task_id"],
        "AWAITING_TOOL_APPROVAL",
        agent="System",
        action=f"Waiting for approval to call {str(pending.get('tool_name', 'connected tool'))[:180]}.",
    )
    save_graph_state(state["task_id"], dict(state))
    return {}


def _write(state: AgentState) -> dict[str, Any]:
    if state.get("draft"):
        return {}
    draft = WritingAgent().run(state["task_id"], state["prompt"])
    return {"draft": draft}


def _approval_gate(state: AgentState) -> dict[str, Any]:
    if state.get("approved"):
        return {}
    transition(
        state["task_id"],
        "AWAITING_APPROVAL",
        result=state.get("draft"),
        agent="System",
        action="Draft is ready; workflow paused for human review.",
    )
    save_graph_state(state["task_id"], dict(state))
    return {}


def _finalize(state: AgentState) -> dict[str, Any]:
    if not state.get("approved"):
        raise RuntimeError("The finalization step requires a human approval decision.")
    draft = state.get("draft", "").strip()
    if not draft:
        raise RuntimeError("The approved draft is missing.")
    result = draft
    if state.get("feedback", "").strip():
        result += f"\n\nHuman review note: {state['feedback'].strip()[:1000]}"
    transition(
        state["task_id"],
        "COMPLETED",
        result=result,
        agent="System",
        action="Human-approved draft was saved as the final result.",
    )
    return {"final_result": result}


def _route_after_gate(state: AgentState) -> str:
    return "finalize" if state.get("approved") else END


def _route_after_research(state: AgentState) -> str:
    return "tool_approval" if state.get("pending_approval") else "write"


def build_langgraph():
    graph = StateGraph(AgentState)
    graph.add_node("research", _research)
    graph.add_node("tool_approval", _tool_approval_gate)
    graph.add_node("write", _write)
    graph.add_node("human_approval", _approval_gate)
    graph.add_node("finalize", _finalize)
    graph.add_edge(START, "research")
    graph.add_conditional_edges(
        "research",
        _route_after_research,
        {"tool_approval": "tool_approval", "write": "write"},
    )
    graph.add_edge("tool_approval", END)
    graph.add_edge("write", "human_approval")
    graph.add_conditional_edges(
        "human_approval", _route_after_gate, {"finalize": "finalize", END: END}
    )
    graph.add_edge("finalize", END)
    return graph.compile()


def run_langgraph_phase(task_id: str, prompt: str) -> None:
    transition(task_id, "RUNNING", agent="System", action="LangGraph workflow started.")
    state: AgentState = {
        "task_id": task_id,
        "prompt": prompt,
        "findings_key": "",
        "draft": "",
        "errors": [],
        "approved": False,
        "feedback": "",
        "final_result": "",
    }
    build_langgraph().invoke(state)


def resume_langgraph_phase(task_id: str, approved: bool, feedback: str) -> None:
    from src.agents.scratchpad import read_graph_state

    state = read_graph_state(task_id)
    if not state:
        raise RuntimeError("The saved LangGraph state is no longer available.")
    state["approved"] = approved
    state["feedback"] = feedback[:2000]
    if not approved:
        transition(task_id, "REJECTED", agent="System", action="Human rejected the draft.")
        return
    build_langgraph().invoke(state)


def resume_langgraph_tool_approval(task_id: str, call_id: str, approved: bool) -> None:
    from src.agents.scratchpad import read_graph_state

    state = read_graph_state(task_id)
    if not state:
        raise RuntimeError("The saved LangGraph state is no longer available.")
    if approved:
        execute_pending_tool_sync(task_id, call_id)
    transition(task_id, "RUNNING", agent="System", action="Tool approval was resolved; research is resuming.")
    state["findings_key"] = ""
    state["pending_approval"] = None
    state["resume_tool"] = True
    build_langgraph().invoke(state)
