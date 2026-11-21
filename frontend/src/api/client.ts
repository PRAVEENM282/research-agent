import type {
  ActivityEntry,
  ConnectionInput,
  ConnectionSummary,
  RuntimeSettings,
  Session,
  SourceArtifact,
  Task,
  TaskList,
  TaskStatus,
  ToolApproval,
  Workspace,
} from "./types";
import { ApiError } from "./types";

let csrfToken = "";
export function setCsrfToken(value: string) {
  csrfToken = value;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const method = (init?.method ?? "GET").toUpperCase();
  const headers = new Headers(init?.headers);
  if (init?.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  if (!new Set(["GET", "HEAD", "OPTIONS"]).has(method) && csrfToken) {
    headers.set("X-CSRF-Token", csrfToken);
  }
  const response = await fetch(path, { ...init, headers, credentials: "same-origin" });
  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const error = payload as { error?: { message?: string; code?: string } } | null;
    throw new ApiError(
      error?.error?.message ?? `Request failed with status ${response.status}.`,
      response.status,
      error?.error?.code,
    );
  }
  return payload as T;
}

export const api = {
  getSession: () => request<Session>("/api/v1/auth/me"),
  getAuthConfig: () => request<{ oidc_available: boolean }>("/api/v1/auth/config"),
  logout: () => request<void>("/api/v1/auth/logout", { method: "POST" }),
  listTasks: (params: { status?: string; limit?: number; offset?: number } = {}) => {
    const query = new URLSearchParams();
    for (const [key, value] of Object.entries(params)) if (value !== undefined && value !== "") query.set(key, String(value));
    return request<TaskList>(`/api/v1/tasks${query.size ? `?${query}` : ""}`);
  },
  getTask: (id: string) => request<Task>(`/api/v1/tasks/${encodeURIComponent(id)}`),
  createTask: (prompt: string) =>
    request<{ task_id: string; status: TaskStatus }>("/api/v1/tasks", { method: "POST", body: JSON.stringify({ prompt }) }),
  approveTask: (id: string, approved: boolean, feedback = "") =>
    request<{ task_id: string; status: TaskStatus }>(`/api/v1/tasks/${encodeURIComponent(id)}/approve`, {
      method: "POST",
      body: JSON.stringify({ approved, feedback }),
    }),
  getWorkspace: (id: string) => request<Workspace>(`/api/v1/tasks/${encodeURIComponent(id)}/workspace`),
  getActivity: (id: string) => request<{ task_id: string; entries: ActivityEntry[] }>(`/api/v1/tasks/${encodeURIComponent(id)}/activity`),
  getSources: (id: string) => request<{ task_id: string; sources: SourceArtifact[] }>(`/api/v1/tasks/${encodeURIComponent(id)}/sources`),
  listToolApprovals: (id: string) => request<ToolApproval[]>(`/api/v1/tasks/${encodeURIComponent(id)}/tool-approvals`),
  decideToolApproval: (id: string, callId: string, approved: boolean) =>
    request<{ task_id: string; call_id: string; status: string }>(
      `/api/v1/tasks/${encodeURIComponent(id)}/tool-approvals/${encodeURIComponent(callId)}`,
      { method: "POST", body: JSON.stringify({ approved }) },
    ),
  submitFeedback: (id: string, rating: "helpful" | "unhelpful", comment = "") =>
    request<{ saved: boolean }>(`/api/v1/tasks/${encodeURIComponent(id)}/feedback`, {
      method: "POST",
      body: JSON.stringify({ rating, comment }),
    }),
  getSettings: () => request<RuntimeSettings>("/api/v1/settings"),
  listConnections: () => request<ConnectionSummary[]>("/api/v1/connections"),
  createConnection: (body: ConnectionInput) => request<ConnectionSummary>("/api/v1/connections", { method: "POST", body: JSON.stringify(body) }),
  updateConnection: (id: string, body: ConnectionInput) => request<ConnectionSummary>(`/api/v1/connections/${encodeURIComponent(id)}`, { method: "PUT", body: JSON.stringify(body) }),
  deleteConnection: (id: string) => request<void>(`/api/v1/connections/${encodeURIComponent(id)}`, { method: "DELETE" }),
  testConnection: (id: string) => request<{ ok: boolean; tool_count?: number; error?: string }>(`/api/v1/connections/${encodeURIComponent(id)}/test`, { method: "POST" }),
  discoverTools: (id: string) => request<{ name: string; description: string; input_schema: Record<string, unknown>; configured_read_only: boolean; enabled: boolean }[]>(`/api/v1/connections/${encodeURIComponent(id)}/tools`),
};
