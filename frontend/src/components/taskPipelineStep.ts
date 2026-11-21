import type { TaskStatus } from "../api/types";

export function getPipelineStep(status: TaskStatus) {
  if (status === "PENDING") return -1;
  if (status === "RUNNING") return 1;
  if (status === "AWAITING_APPROVAL") return 2;
  if (status === "RESUMED") return 3;
  if (status === "COMPLETED") return 4;
  return status === "REJECTED" ? 2 : 1;
}
