export type TaskStatus =
  | "PENDING"
  | "RUNNING"
  | "AWAITING_APPROVAL"
  | "AWAITING_TOOL_APPROVAL"
  | "RESUMED"
  | "COMPLETED"
  | "FAILED"
  | "REJECTED";

export type AuditEntry = { agent: string; action: string; timestamp: string };
export type Task = {
  id: string;
  prompt: string;
  status: TaskStatus;
  result: string | null;
  agent_logs: AuditEntry[] | null;
  created_at: string;
  updated_at: string;
};
export type TaskList = { items: Task[]; total: number; limit: number; offset: number };
export type ActivityEntry = {
  timestamp: string;
  task_id: string;
  agent_name: string;
  action_details: string;
  level: string;
  event?: string;
};
export type Workspace = { task_id: string; workspace: Record<string, unknown> };
export type SourceArtifact = {
  id: string;
  title: string;
  url: string;
  domain: string;
  retrieved_at: string;
  excerpt: string;
  status: string;
};
export type ToolApproval = {
  call_id: string;
  tool_name: string;
  arguments: Record<string, unknown>;
  status: string;
  created_at: string;
};
export type CurrentUser = { id: string; issuer: string; subject: string; email: string; display_name: string | null };
export type Session = { user: CurrentUser; csrf_token: string };
export type RuntimeSettings = {
  llm_provider: string;
  llm_model: string;
  llm_configured: boolean;
  search_provider: string;
  search_configured: boolean;
};
export type ConnectionInput = {
  name: string;
  url: string;
  bearer_token?: string;
  enabled_tools: string[];
  read_only_tools: string[];
};
export type ConnectionSummary = {
  id: string;
  name: string;
  url: string;
  credential_configured: boolean;
  enabled_tools: string[];
  read_only_tools: string[];
};

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly code = "request_error",
  ) {
    super(message);
    this.name = "ApiError";
  }
}
