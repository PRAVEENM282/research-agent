# Handoff Research Workbench Implementation Plan

> **For agentic workers:** Use `executing-plans` to implement this plan task by task. Do not delegate work to agents. Steps use checkbox syntax for tracking.

**Goal:** Turn Handoff into a private, authenticated research workbench that performs real web research, supports guarded xAI/MCP tools, and presents a clear full-width run and review experience.

**Architecture:** FastAPI remains the same-origin API and OIDC relying party. PostgreSQL stores users, sessions, task ownership, research sources, MCP connections, tool-call approvals, and task data; Redis remains workflow scratch space and events. SearXNG discovers pages, Trafilatura extracts static-page content, and provider adapters execute validated tools in workers. React/Vite remains the UI; its routes become the signed-in workbench, docs, tools, and settings.

**Tech Stack:** Python 3.11, FastAPI, Authlib 1.9.10, SQLAlchemy 2, PostgreSQL 15, Redis, `trafilatura==2.3.1`, MCP Python SDK 2.3.0 over Streamable HTTP, `cryptography==50.0.2`, React 18, TypeScript, Vite, Tailwind 3, existing Radix/shadcn primitives, Docker Compose, Caddy.

## Global Constraints

- Use configurable OIDC Authorization Code + PKCE, validate issuer/state/nonce, and keep client secrets on the server.
- Support either an explicit verified-email allowlist or an explicit open-registration setting for any verified account at the configured OIDC issuer; resource ownership remains per user.
- Every task, source, connection, approval, activity, and WebSocket operation is private to its owner.
- Keep legacy tasks unowned and invisible until the explicitly configured, allowlisted bootstrap email completes verified OIDC sign-in; assign them in that authenticated transaction without requiring the provider's opaque subject in advance.
- Never use fixture results as live research. Live search failures and offline writing must be identified truthfully.
- SearXNG handles result discovery; Trafilatura handles static page extraction; Crawl4AI is optional and not enabled by default.
- Apply bounded query count, result count, redirects, fetch time, bytes, host rate, and tool-call count.
- Block private, loopback, link-local, and cloud metadata destinations for public URL fetches; re-check every redirect.
- xAI, OpenAI, Anthropic, Gemini, and Ollama use one bounded provider-neutral tool contract.
- Expose only allowlisted MCP tools. Require explicit approval before executing a tool classified as mutating.
- Encrypt MCP credentials at rest and never return them from the API or write them to logs.
- Temporal stays primary; Celery + LangGraph remains supported with equivalent approval behavior.
- Remove Architecture and Status UI. `/docs` is the product guide; FastAPI's interactive docs move to `/api/reference`.
- Keep the existing UI stack and local fonts; use full available desktop width, 320 px mobile support, keyboard focus, and reduced-motion behavior.
- Do not add or run automated tests during this execution. Use static compile/lint/build checks only.

---

## File Map

### Backend

- `src/config/settings.py`, `.env.example`: OIDC, search, encryption, xAI, and safe fetch limits.
- `src/db/models.py`, `src/db/engine.py`, `src/db/repository.py`: identity, sessions, task ownership, source artifacts, user feedback, MCP connections, pending tool approvals, and additive startup migrations.
- `src/api/auth.py`, `src/api/dependencies.py`: OIDC routes, session authentication, CSRF, and current-user dependencies.
- `src/api/tasks.py`, `src/api/approvals.py`, `src/api/feedback.py`, `src/api/websocket.py`, `src/api/schemas.py`: ownership checks, sources, user feedback, tool approval, and response contracts.
- `src/api/connections.py`, `src/api/settings.py`: per-user MCP connection management and safe runtime settings.
- `src/agents/search.py`, `src/agents/extract.py`, `src/agents/url_policy.py`: SearXNG discovery, safe HTTP fetch, and Trafilatura extraction.
- `src/agents/tool_registry.py`, `src/agents/mcp_client.py`, `src/agents/llm.py`, `src/agents/research_agent.py`, `src/agents/writing_agent.py`: provider-neutral tool loop, MCP execution, xAI adapter, real prompt-driven research, and citations.
- `src/workflows/temporal_workflow.py`, `src/workflows/temporal_activities.py`, `src/workflows/langgraph_workflow.py`: durable approval/resume around mutating tools.
- `src/main.py`: auth, settings, connection, task, and source routers; docs URLs; request security middleware.

### Frontend and deployment

- `frontend/src/App.tsx`, `frontend/src/components/SiteLayout.tsx`, `frontend/src/context/AuthContext.tsx`, `frontend/src/components/ProtectedRoute.tsx`: authenticated routing and shell.
- `frontend/src/pages/{Landing,Login,Workspace,History,TaskDetail,Tools,Settings,Documentation,NotFound}.tsx`: product routes and page content.
- `frontend/src/components/{RunTrace,SourcePanel,ToolCallReview}.tsx`, `frontend/src/api/{client,types}.ts`: source-aware run view, approval UI, and session/CSRF API client.
- `frontend/src/styles/{global,tokens,components}.css`: full-width layout, page hierarchy, responsive behavior, and action-based motion.
- `frontend/Caddyfile`, `frontend/vite.config.ts`: route `/docs` to the SPA and API schema/docs to FastAPI.
- `docker-compose.yml`, `docker-compose.prod.yml`, `Dockerfile`, `README.md`, `deploy/searxng/settings.yml`: SearXNG, environment wiring, resource boundaries, and deployment steps.

## Shared Contracts

- `CurrentUser`: `{ id: UUID, issuer: str, subject: str, email: str, display_name: str | None }`.
- `SessionResponse`: `{ user: CurrentUser, csrf_token: str }`.
- `TaskStatus`: current values plus `AWAITING_TOOL_APPROVAL`.
- `SourceArtifact`: `{ id: UUID, title: str, url: str, domain: str, retrieved_at: datetime, excerpt: str, status: str }`.
- `ToolContext`: `{ owner_id: UUID, task_id: UUID, run_id: str, call_id: str }`.
- `ToolResult`: `{ status: Literal["ok", "error", "approval_required"], content: dict[str, Any], error_code: str | None }`.
- `ResearchFindings`: `{ queries: list[str], sources: list[SourceArtifact], collected_at: datetime }`.
- `MCPConnectionCreate`: `{ name: str, url: AnyHttpUrl, bearer_token: SecretStr | None, enabled_tools: list[str], read_only_tools: list[str] }`.
- `ConnectionSummary`: `{ id: UUID, name: str, url: str, credential_configured: bool, enabled_tools: list[str] }`.
- `MCPTool`: `{ name: str, description: str, input_schema: dict[str, Any], configured_read_only: bool }`.
- `ApprovalState`: `{ call_id: str, task_id: UUID, status: Literal["PENDING_APPROVAL", "APPROVED", "RUNNING", "REJECTED", "SUCCEEDED", "FAILED", "INDETERMINATE"] }`.
- `RuntimeSettingsResponse`: `{ llm_provider: str, llm_model: str, llm_configured: bool, search_provider: str, search_configured: bool }`.

## Tasks

### Task 1: Configuration, identity schema, and additive migration

**Files:** `requirements.txt`, `.env.example`, `src/config/settings.py`, `src/db/models.py`, `src/db/engine.py`, new `src/db/migrations.py`.

**Interfaces:**

- `Settings` adds `oidc_issuer_url`, `oidc_client_id`, `oidc_client_secret`, `oidc_redirect_uri`, `oidc_allowed_emails`, `oidc_allow_any_emails`, `oidc_bootstrap_email`, `oidc_session_secret`, `app_encryption_key`, `searxng_url`, `crawl4ai_url`, `research_max_results`, `research_max_pages`, `research_max_bytes`, `research_timeout_seconds`, `xai_api_key`, and `llm_provider="xai"` support.
- SQLAlchemy models: `User`, `UserSession`, `TaskOwner`, `TaskSource`, `TaskFeedback`, `MCPConnection`, and `PendingToolApproval`.
- `run_schema_migrations(connection)` creates new tables without altering the approved seven-column `tasks` table.

- [ ] Add exact pinned dependencies: `Authlib==1.9.10`, `itsdangerous==2.2.0`, `cryptography==50.0.2`, `mcp==2.3.0`, and `trafilatura==2.3.1`.
- [ ] Add validated settings, requiring OIDC issuer/client/secret/redirect URI, at least one verified email in `OIDC_ALLOWED_EMAILS`, session key, and encryption key in production.
- [ ] Add identity, ownership, feedback, and source models with unique `(issuer, subject)` and `(task_id)` constraints, plus user-scoped connection indexes.
- [ ] Add migration version tracking and create identity/artifact tables additively from `init_db_sync()`.
- [ ] Keep tasks without owners invisible; after OIDC verifies an allowlisted email equal to `OIDC_BOOTSTRAP_EMAIL`, assign them to the authenticated `(issuer, subject)` in the same transaction as session creation.
- [ ] Change production `SEED_DEMO_DATA` default to false. Keep any demo seed local-only and ensure it is not exposed as a live researched run.
- [ ] Add `.env.example` entries for all settings with safe placeholders and no secret values.

Configuration shape:

```env
OIDC_ISSUER_URL=
OIDC_CLIENT_ID=
OIDC_CLIENT_SECRET=
OIDC_REDIRECT_URI=https://YOUR_DOMAIN/api/v1/auth/callback
OIDC_ALLOWED_EMAILS=
OIDC_BOOTSTRAP_EMAIL=
APP_ENCRYPTION_KEY=
SEARXNG_URL=http://searxng:8080
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
XAI_API_KEY=
```

**Completion condition:** API and worker can load the expanded settings, and startup migration creates new tables while retaining the existing `tasks` columns.

### Task 2: OIDC session lifecycle and authenticated API dependency

**Files:** add `src/api/auth.py`, `src/api/dependencies.py`; modify `src/main.py`, `src/config/settings.py`, `requirements.txt`.

**Interfaces:**

```python
async def require_user(request: Request) -> CurrentUser: ...
async def oidc_login(request: Request) -> RedirectResponse: ...
async def oidc_callback(request: Request) -> RedirectResponse: ...
async def current_session(user: CurrentUser = Depends(require_user)) -> SessionResponse: ...
async def logout(request: Request, user: CurrentUser = Depends(require_user)) -> Response: ...
```

- [ ] Register Authlib's Starlette OIDC client using discovery metadata, `openid profile email`, and `code_challenge_method="S256"`.
- [ ] Add signed transient Starlette session middleware for OIDC state, nonce, and PKCE verifier; keep durable app login sessions in the PostgreSQL opaque-session table.
- [ ] Add `/api/v1/auth/login`, `/api/v1/auth/callback`, `/api/v1/auth/me`, and `POST /api/v1/auth/logout`.
- [ ] Require a verified email; enforce `OIDC_ALLOWED_EMAILS` unless `OIDC_ALLOW_ANY_EMAILS=true` explicitly enables open registration.
- [ ] Upsert user by `(issuer, sub)`, store an opaque random session token hash in PostgreSQL, and set only the raw token in an HttpOnly, Secure, SameSite=Lax cookie.
- [ ] Derive a CSRF token as an HMAC of the session token, return it from `/me`, and require `X-CSRF-Token` plus same-origin validation for state-changing requests.
- [ ] Revoke the server-side session and clear the cookie on logout. Do not log authorization codes, cookies, client secrets, or tokens.
- [ ] Add middleware/dependency behavior that returns the existing safe error envelope with 401 for missing/expired session and 403 for CSRF/origin failure.

**Completion condition:** OIDC routes create, resolve, expire, and revoke server-side sessions; no secret or token is present in frontend payloads or application logs.

### Task 3: Ownership checks for task, approval, workspace, activity, and WebSocket APIs

**Files:** add `src/api/feedback.py`, `src/api/settings.py`; modify `src/db/repository.py`, `src/api/tasks.py`, `src/api/approvals.py`, `src/api/websocket.py`, `src/api/schemas.py`, `src/main.py`.

**Interfaces:**

```python
async def create_task(prompt: str, owner_id: UUID) -> Task: ...
async def get_owned_task(task_id: UUID, owner_id: UUID) -> Task | None: ...
async def list_owned_tasks(owner_id: UUID, status: str | None, limit: int, offset: int) -> tuple[list[Task], int]: ...
async def get_runtime_settings(user: CurrentUser) -> RuntimeSettingsResponse: ...
```

- [ ] Require `CurrentUser` on all task list/create/detail/source/activity/workspace/approval routes.
- [ ] Add owner-scoped `POST /api/v1/tasks/{id}/feedback` with a constrained helpful/unhelpful value and optional bounded comment; allow one current value per owner and task.
- [ ] Add authenticated `GET /api/v1/settings` returning only the provider/model/search names and configured booleans in `RuntimeSettingsResponse`.
- [ ] Write the owner mapping in the same database transaction as task + outbox creation.
- [ ] Add ownership filters to reads and approval updates. Return 404 for both nonexistent and other-user task IDs.
- [ ] Authorize the WebSocket before accept; verify both session and `Origin`, then stream only the owned task channel.
- [ ] Restrict status/system routes to internal health use or remove them from any user-facing API contract; `/health` stays unauthenticated for probes.
- [ ] Leave unowned legacy tasks private during startup; claim them only after verified sign-in by the explicit, allowlisted bootstrap email, in the same transaction as session creation.

**Completion condition:** every resource API has an explicit owner predicate and never returns a cross-user task identifier, event, workspace, or approval result.

### Task 4: Prompt-driven search, safe extraction, and durable sources

**Files:** add `src/agents/search.py`, `src/agents/extract.py`, `src/agents/url_policy.py`; modify `src/agents/tools.py`, `src/agents/research_agent.py`, `src/agents/scratchpad.py`, `src/db/models.py`, `src/db/repository.py`, `src/api/tasks.py`, `src/api/schemas.py`.

**Interfaces:**

```python
class SearchHit(BaseModel):
    title: str
    url: AnyHttpUrl
    snippet: str = ""

async def search_web(query: str, limit: int) -> list[SearchHit]: ...
async def fetch_and_extract(url: str, owner_id: UUID) -> SourceArtifact: ...
async def validate_public_http_url(url: str) -> str: ...
async def save_sources(task_id: UUID, sources: list[SourceArtifact]) -> None: ...
```

- [ ] Implement SearXNG `/search?q=...&format=json` adapter with explicit timeout, status validation, result limit, and URL normalization.
- [ ] Require JSON output to be enabled in bundled SearXNG config; document that public SearXNG instances may disable JSON and are not a production guarantee.
- [ ] Before every fetch and redirect, validate scheme, resolve the destination, reject private/loopback/link-local/metadata IPs, cap redirects and response bytes, and re-check the final host.
- [ ] Fetch HTML with the application's bounded HTTP client and pass HTML to Trafilatura for text + metadata extraction; do not let extraction libraries independently fetch arbitrary URLs.
- [ ] Derive search intent from the submitted prompt and remove the fixed LangGraph/CrewAI query. Make `__FLAKY_TEST__` available only to explicit local fault-injection mode, never as ordinary query behavior.
- [ ] Store title, URL, domain, retrieval time, bounded excerpt, and extraction outcome in Postgres `TaskSource`; return sources only when task ownership is verified.
- [ ] Replace the simulated tool from `ALLOWED_TOOLS`; unconfigured/failed discovery must fail the research stage with a truthful user-facing reason.

**Completion condition:** an ordinary prompt is sent to the configured search service, extracted sources are persisted, and every source URL is subject to the same public-network policy.

### Task 5: Provider-neutral tool loop and xAI adapter

**Files:** add `src/agents/tool_registry.py`; modify `src/agents/policy.py`, `src/agents/llm.py`, `src/agents/research_agent.py`, `src/config/settings.py`, `.env.example`, `docker-compose.yml`, `docker-compose.prod.yml`.

**Interfaces:**

```python
class ToolSpec(BaseModel):
    name: str
    description: str
    parameters: dict[str, Any]
    read_only: bool

async def call_tool(name: str, arguments: dict[str, Any], context: ToolContext) -> ToolResult: ...
def get_chat_model() -> BaseChatModel: ...
async def invoke_research_tools(prompt: str, owner_id: UUID, task_id: UUID) -> ResearchFindings: ...
```

- [ ] Add `xai` to provider settings; initialize `ChatOpenAI` with `base_url="https://api.x.ai/v1"`, `settings.xai_api_key`, and configured `LLM_MODEL` unless an explicit compatible base URL is set.
- [ ] Normalize tool schemas and calls across OpenAI-compatible/xAI, Anthropic, Gemini, and Ollama adapters. Fail closed if a configured adapter cannot safely return a validated tool call.
- [ ] Replace the single-name allowlist with user- and server-policy intersection: built-in search/extract tools plus only the owner’s enabled MCP tool names.
- [ ] Validate JSON arguments, provider call count, per-call timeout, tool output size, and total run budget before execution.
- [ ] Record sanitized tool name, call ID, status, duration, and bounded error category; redact credentials and sensitive argument values.
- [ ] Update offline-key detection to inspect the selected provider's key, including `XAI_API_KEY`. Keep the deterministic writer explicitly labeled; it must consume live source records and must not recreate canned framework summaries.
- [ ] Pass provider credentials to API and worker containers without baking them into images or returning them to `/api/v1/settings`.

**Completion condition:** selecting `LLM_PROVIDER=xai` sends tool schemas to Grok and Handoff executes only registered, policy-approved tools.

### Task 6: User-managed MCP connections and approval before side effects

**Files:** add `src/agents/mcp_client.py`, `src/api/connections.py`; modify `src/db/models.py`, `src/db/repository.py`, `src/api/schemas.py`, `src/agents/tool_registry.py`, `src/agents/policy.py`, `src/workflows/temporal_workflow.py`, `src/workflows/temporal_activities.py`, `src/workflows/langgraph_workflow.py`, `src/worker/tasks.py`.

**Interfaces:**

```python
async def list_connections(owner_id: UUID) -> list[ConnectionSummary]: ...
async def create_connection(owner_id: UUID, body: MCPConnectionCreate) -> ConnectionSummary: ...
async def discover_connection_tools(owner_id: UUID, connection_id: UUID) -> list[MCPTool]: ...
async def approve_tool_call(owner_id: UUID, task_id: UUID, call_id: str, approved: bool) -> ApprovalState: ...
```

- [ ] Use MCP Python SDK 2.3.0 with Streamable HTTP. Restrict configured remote URLs to HTTPS and apply destination/redirect policy before opening a connection.
- [ ] Store connection name, endpoint, owner, selected tool names, read-only classification, and AES-GCM-encrypted bearer credential. Require `APP_ENCRYPTION_KEY`; never persist plaintext.
- [ ] Add list/create/update/delete/test-connection endpoints with ownership filtering. The API returns `credential_configured: true|false`, never the credential.
- [ ] Discover remote tools but expose only names explicitly enabled by the user. Do not trust MCP annotations alone to classify a tool as read-only.
- [ ] Store a unique tool-call ledger row with sanitized arguments and states `PENDING_APPROVAL`, `APPROVED`, `RUNNING`, `SUCCEEDED`, `FAILED`, or `INDETERMINATE`; never automatically retry a side-effecting call after an ambiguous timeout.
- [ ] Add `AWAITING_TOOL_APPROVAL` to task status contracts. Display the requested tool, exact bounded arguments, and the effects classification before approval.
- [ ] Implement durable wait/resume for Temporal using a workflow signal and for Celery + LangGraph using persisted state. Approval is scoped to the task owner and call ID; rejection returns a denial result to the agent without executing the tool.
- [ ] Update task status transitions and audit events so repeated approval requests and duplicate tool call IDs are idempotent.

**Completion condition:** a connected user can allow a read-only MCP tool; a mutating tool waits durably for owner approval and cannot execute twice due to a workflow retry.

### Task 7: Full-width authenticated frontend and route replacement

**Files:** add `frontend/src/context/AuthContext.tsx`, `frontend/src/components/ProtectedRoute.tsx`, `frontend/src/pages/Login.tsx`, `frontend/src/pages/Workspace.tsx`, `frontend/src/pages/Tools.tsx`, `frontend/src/pages/Settings.tsx`, `frontend/src/pages/Documentation.tsx`; modify `frontend/src/App.tsx`, `frontend/src/components/SiteLayout.tsx`, `frontend/src/pages/Landing.tsx`, `frontend/src/pages/History.tsx`, `frontend/src/api/client.ts`, `frontend/src/api/types.ts`, `frontend/src/styles/global.css`, `frontend/src/styles/tokens.css`, `frontend/src/styles/components.css`.

**Interfaces:**

```ts
type AuthState = { user: User | null; csrfToken: string | null; loading: boolean };
type MCPConnection = { id: string; name: string; url: string; credential_configured: boolean; enabled_tools: string[] };
type TaskSource = { id: string; title: string; url: string; domain: string; retrieved_at: string; excerpt: string; status: string };
```

- [ ] Make the API client send `credentials: "include"`; add `X-CSRF-Token` to POST/PUT/PATCH/DELETE using the in-memory auth context token.
- [ ] Add auth loading, signed-out login, protected route, sign-out, and 401 session-expiry behavior without storing access/session tokens in localStorage.
- [ ] Replace top navigation/footer links with a compact desktop navigation rail: Workspace, Runs, Tools, Documentation, Settings. Remove Architecture and Status routes and links.
- [ ] Build Workspace with a new-research composer, real recent runs, and only the current user's pending reviews; do not include fixture example metrics or fake “live” status.
- [ ] Update shell CSS to full viewport width, 220 px desktop rail, fluid content, 24–32 px gutters, mobile menu, 320 px minimum support, and readable report measure.
- [ ] Keep bundled Fira fonts and current Radix/shadcn primitives; do not add a React 19/Tailwind 4 component framework migration.
- [ ] Make `/` concise for signed-out users and route signed-in users to `/workspace`.

**Completion condition:** unauthenticated users see login/landing only; signed-in pages use the full viewport and all navigation routes match the spec.

### Task 8: Evidence-first run detail, settings, tools, and documentation hub

**Files:** add `frontend/src/components/RunTrace.tsx`, `frontend/src/components/SourcePanel.tsx`, `frontend/src/components/ToolCallReview.tsx`; modify `frontend/src/pages/TaskDetail.tsx`, `frontend/src/pages/History.tsx`, `frontend/src/pages/Tools.tsx`, `frontend/src/pages/Settings.tsx`, `frontend/src/pages/Documentation.tsx`, `frontend/src/api/client.ts`, `frontend/src/api/types.ts`, `frontend/src/App.tsx`.

- [ ] Add source retrieval to the task detail API query and render citation links that open the matching source; show title, domain, retrieved time, bounded excerpt, and extraction errors.
- [ ] Render real workflow/tool events in one trace with attempts and outcomes; show only provider-reported metrics and measured durations.
- [ ] Add approve/reject draft UI and separate approve/deny UI for a pending tool call. Explain what will execute before the user confirms.
- [ ] Add a helpful/unhelpful feedback control to completed runs and persist the current user's choice with the optional bounded comment.
- [ ] Add Tools page for owner-scoped MCP endpoints, enabled tool selection, test connection, and write-only bearer credential entry. Confirm deletion and revoke on the backend.
- [ ] Add Settings page for profile/sign-out and actual environment-managed provider/model/search configuration state; do not let the browser edit `.env` or show key text.
- [ ] Back Settings with an authenticated `GET /api/v1/settings` response that includes only provider/model/search names and configured booleans, never secret values.
- [ ] Replace `ApiReference.tsx` with Documentation sections: setup, provider and search configuration, MCP connections, authentication, API schemas/examples, status transitions, errors, and WebSocket events.
- [ ] Move API examples under `/docs#api`; link the interactive schema at `/api/reference` and raw `/openapi.json`.
- [ ] Remove `Architecture.tsx` and `SystemStatus.tsx` imports/routes; keep `/health` available only as an operational probe.
- [ ] Provide loading, empty, 401/403, network error, source-fetch failure, and approval states. Use action transitions only and respect `prefers-reduced-motion`.

**Completion condition:** a user can follow a real task from submission through citations and human review, and can inspect/manage permitted tools without seeing credentials.

### Task 9: SearXNG, Caddy, Compose, and deployment documentation

**Files:** add `deploy/searxng/settings.yml`; modify `docker-compose.yml`, `docker-compose.prod.yml`, `frontend/Caddyfile`, `frontend/vite.config.ts`, `.env.example`, `README.md`, `src/main.py`, `src/config/settings.py`.

- [ ] Add a private-only Compose SearXNG service pinned to `searxng/searxng:2026.11.20-cd6d28091`, enable JSON response format, set an instance secret, and expose no host port.
- [ ] Set API/worker `SEARXNG_URL=http://searxng:8080`; add a bounded health check and resource limit. Do not bundle Crawl4AI Chromium into the default stack; allow an optional configured `CRAWL4AI_URL` fallback.
- [ ] Wire OIDC, xAI, encryption, fetch limits, and SearXNG settings to API and worker; use empty safe defaults only in local examples.
- [ ] Set FastAPI `docs_url="/api/reference"`, `redoc_url="/api/redoc"`, and `openapi_url="/openapi.json"`.
- [ ] Change Caddy so `/api/*`, `/ws/*`, `/health`, and `/openapi.json` proxy to FastAPI, while `/docs` and ordinary routes fall through to the SPA. Give `/api/reference` CSP allowance for the schema UI assets.
- [ ] Change Vite proxy rules to proxy auth/API/schema/WebSocket routes and not proxy `/docs` to FastAPI.
- [ ] Document OIDC client registration, authorized identities, bootstrap owner migration, key rotation, SearXNG JSON config, MCP encryption, xAI setup, and resource requirements.
- [ ] State clearly that EC2 Free Tier eligibility/resources depend on the AWS account and instance; the default stack is not guaranteed to fit or cost zero.

**Completion condition:** Compose supplies an internal SearXNG endpoint and browser/API routes resolve to the intended service.

### Task 10: Static checks and application handoff

**Files:** touched backend/frontend/deployment files.

- [ ] Run `python -m compileall src` to catch backend syntax errors.
- [ ] Run `npm run lint` and `npm run build` from `frontend/` to catch type/lint/build errors.
- [ ] Do not run `pytest`, Vitest, or add tests under this execution's verification constraint.
- [ ] If Docker is available, start `docker compose up --build -d`; report any SearXNG upstream or provider limitation distinctly from application startup.
- [ ] Start the frontend/API stack after code checks and return the actual local frontend URL and any required OIDC/provider environment setup.
- [ ] Report unresolved live-provider, OIDC callback, public URL, and AWS deployment steps as pending instead of claiming they were verified.

## Review checklist

- Identity policy and ownership cover HTTP, WebSocket, worker approval, MCP connection, and source artifacts.
- Existing orphan tasks remain excluded from owner-scoped reads until the verified bootstrap account claims them.
- Search implementation has separate discovery and extraction adapters; every fetched URL is guarded and bounded.
- Provider adapters never execute an unregistered tool; side-effecting tools wait for approval and have an idempotent ledger.
- Offline text is labeled, sources are durable, and no demo facts masquerade as live research.
- `/docs` routes to the product guide; the FastAPI docs no longer intercept it.
- UI uses real user-owned data and has no Architecture/Status page, fake metrics, or secret values.
- No user secret was printed, committed, or included in documentation.

## Source references checked during planning

- [Authlib OIDC and PKCE docs](https://docs.authlib.org/en/stable/oauth2/client/web/index.html)
- [xAI tool calling](https://docs.x.ai/developers/tools/function-calling) and [OpenAI-compatible API reference](https://docs.x.ai/developers/rest-api-reference/inference)
- [MCP Python SDK Streamable HTTP client](https://github.com/modelcontextprotocol/python-sdk/blob/main/docs/client/transports.md)
- [SearXNG Search API](https://docs.searxng.org/dev/search_api.html)
- [Trafilatura on PyPI](https://pypi.org/project/trafilatura/)
