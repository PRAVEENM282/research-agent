import type { TaskStatus } from "../../api/types";

const labels: Record<TaskStatus, string> = {
  PENDING: "Queued",
  RUNNING: "In progress",
  AWAITING_APPROVAL: "Review needed",
  AWAITING_TOOL_APPROVAL: "Tool approval",
  RESUMED: "Finishing",
  COMPLETED: "Complete",
  FAILED: "Failed",
  REJECTED: "Rejected",
};

export function StatusBadge({ status }: { status: TaskStatus }) {
  const tone = status === "COMPLETED" ? "success" : status === "FAILED" || status === "REJECTED" ? "failure" : status === "AWAITING_APPROVAL" || status === "AWAITING_TOOL_APPROVAL" ? "human" : status === "PENDING" ? "neutral" : "agent";
  return <span className={`status-badge badge-${tone}`}><span className="badge-dot" aria-hidden="true" />{labels[status]}</span>;
}
