from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from src.workflows import temporal_activities as activities


ACTIVITY_RETRY = RetryPolicy(
    initial_interval=timedelta(seconds=1),
    maximum_interval=timedelta(seconds=5),
    backoff_coefficient=2.0,
    maximum_attempts=3,
)


@workflow.defn
class HandoffWorkflow:
    def __init__(self) -> None:
        self.decision: tuple[bool, str] | None = None
        self.tool_decision: tuple[str, bool] | None = None

    @workflow.signal
    def approve(self, approved: bool, feedback: str = "") -> None:
        if self.decision is None:
            self.decision = (approved, feedback[:2000])

    @workflow.signal
    def approve_tool(self, call_id: str, approved: bool) -> None:
        if self.tool_decision is None:
            self.tool_decision = (call_id[:200], approved)

    @workflow.run
    async def run(self, task_id: str, prompt: str) -> str:
        try:
            await workflow.execute_activity(
                activities.mark_running,
                task_id,
                start_to_close_timeout=timedelta(seconds=20),
                retry_policy=ACTIVITY_RETRY,
            )
            findings = await workflow.execute_activity(
                activities.research,
                args=[task_id, prompt],
                start_to_close_timeout=timedelta(minutes=2),
                retry_policy=ACTIVITY_RETRY,
            )
            while findings.get("pending_approval"):
                approval = findings["pending_approval"]
                call_id = str(approval["call_id"])
                await workflow.execute_activity(
                    activities.await_tool_approval,
                    args=[task_id, approval],
                    start_to_close_timeout=timedelta(seconds=20),
                    retry_policy=ACTIVITY_RETRY,
                )
                await workflow.wait_condition(
                    lambda: self.tool_decision is not None and self.tool_decision[0] == call_id
                )
                _, approved = self.tool_decision
                self.tool_decision = None
                await workflow.execute_activity(
                    activities.resolve_tool_approval,
                    args=[task_id, call_id, approved],
                    start_to_close_timeout=timedelta(minutes=2),
                    retry_policy=RetryPolicy(maximum_attempts=1),
                )
                await workflow.execute_activity(
                    activities.mark_running,
                    task_id,
                    start_to_close_timeout=timedelta(seconds=20),
                    retry_policy=ACTIVITY_RETRY,
                )
                findings = await workflow.execute_activity(
                    activities.research,
                    args=[task_id, prompt],
                    start_to_close_timeout=timedelta(minutes=2),
                    retry_policy=ACTIVITY_RETRY,
                )
            draft = await workflow.execute_activity(
                activities.write_draft,
                args=[task_id, prompt],
                start_to_close_timeout=timedelta(minutes=2),
                retry_policy=ACTIVITY_RETRY,
            )
            await workflow.execute_activity(
                activities.await_approval,
                args=[task_id, draft],
                start_to_close_timeout=timedelta(seconds=20),
                retry_policy=ACTIVITY_RETRY,
            )
            await workflow.wait_condition(lambda: self.decision is not None)
            approved, feedback = self.decision
            if not approved:
                await workflow.execute_activity(
                    activities.reject,
                    task_id,
                    start_to_close_timeout=timedelta(seconds=20),
                    retry_policy=ACTIVITY_RETRY,
                )
                return "REJECTED"
            result = await workflow.execute_activity(
                activities.finalize,
                args=[task_id, draft, feedback],
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=ACTIVITY_RETRY,
            )
            return result
        except Exception:
            await workflow.execute_activity(
                activities.workflow_failed,
                task_id,
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=ACTIVITY_RETRY,
            )
            return "FAILED"
