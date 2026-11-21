# Handoff Multi-Agent Platform Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Build and verify a deployable multi-agent platform with Temporal and Celery + LangGraph execution paths, human approval, and a complete real-API frontend.

**Architecture:** FastAPI and PostgreSQL provide a shared task contract. Redis carries scratchpad and engine state. A Celery bridge dispatches each task to exactly one engine selected by WORKFLOW_ENGINE; Temporal is the default. Both paths share guarded provider and agent services.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy 2, asyncpg, psycopg, Pydantic v2, PostgreSQL 15, Redis, Celery, LangGraph, Temporal Python SDK, React 18, TypeScript, Vite, Tailwind CSS, shadcn/ui primitives, Caddy, Docker Compose.

## Global Constraints

- The API never calls a model in an HTTP request.
- The tasks table has exactly the columns and types in the approved design.
- Statuses are PENDING, RUNNING, AWAITING_APPROVAL, RESUMED, COMPLETED, FAILED, and REJECTED.
- Prompts are non-empty and at most 4000 characters.
- Both engines use the same UUID, status API, agent audit entries, Redis workspace, approval contract, retry policy, and safe error shape.
- The selected workflow engine is persisted in Redis for the lifetime of a task.
- OpenAI, Anthropic, Gemini, Ollama, and deterministic offline mode are configurable through environment variables.
- Agent tools are allowlisted; model output cannot approve a task or invoke arbitrary tools.
- Frontend supports 360px widths, keyboard use, reduced motion, visible focus, and WCAG AA contrast.
- Compose provides healthy db, redis, api, worker, and web services; the Temporal development service and Temporal worker support the default local engine.
- Production deployment uses an external production Temporal service or Temporal Cloud, persistent data, HTTPS, and explicit cost controls.

## File Map

- src/config/: settings and structured logging.
- src/db/: task table, async API access, sync worker access, and idempotent initialization.
- src/api/: task creation, reads, approval, workspace/activity/status, and WebSocket routes.
- src/worker/: Celery dispatch bridge and Temporal worker process.
- src/workflows/: Temporal workflow, activities, Celery + LangGraph path, and shared state.
- src/agents/: guardrails, providers, research/writing nodes, tools, and Redis scratchpad.
- frontend/src/: routes, API client, live-status hook, accessible UI primitives, and page components.
- tests/ and frontend/src/**/*.test.ts: backend and frontend contract coverage.
- Root Compose, Dockerfiles, Makefile, CI, README, and deployment scripts define local and production operation.

## Tasks

### Task 1: Project foundation and configuration

**Files:** requirements.txt, pyproject.toml, .env.example, .gitignore, .dockerignore, LICENSE, src/config/settings.py, src/config/logging_config.py, src/db/models.py, src/db/engine.py, src/db/init.sql, tests/test_settings.py, tests/test_database_schema.py.

**Interfaces:** Settings exposes validated provider, workflow-engine, database, Redis, logging, and rate-limit configuration. Task maps exactly to the approved table schema. init_db() creates the schema idempotently.

- [x] Pin Python dependencies and create the application package layout.
- [x] Implement environment validation, placeholder-key detection, and safe defaults.
- [x] Create the exact task schema, indexes, and update-timestamp trigger.
- [x] Test URL driver conversion, provider defaults, schema columns, and idempotent initialization.

### Task 2: Shared task API and status events

**Files:** src/api/schemas.py, src/api/errors.py, src/api/tasks.py, src/api/approvals.py, src/api/websocket.py, src/api/events.py, src/main.py, src/db/repository.py, tests/test_task_api.py, tests/test_approval_api.py, tests/test_websocket.py.

**Interfaces:** TaskCreate(prompt), ApprovalRequest(approved, feedback), create_task(), get_task(), list_tasks(), approve_task(), and publish_status(task_id, status) define the shared contract.

- [x] Implement create/list/get with async SQLAlchemy and the exact response schemas.
- [x] Make approval a conditional update from AWAITING_APPROVAL; append human audit data atomically.
- [x] Send current DB status before subscribing WebSocket clients to task events.
- [x] Test 202, 404, 409, 422, list pagination, event order, and disconnect cleanup.

### Task 3: Shared agent services, provider switch, and guardrails

**Files:** src/agents/state.py, src/agents/policy.py, src/agents/providers.py, src/agents/tools.py, src/agents/scratchpad.py, src/agents/research.py, src/agents/writer.py, tests/test_policy.py, tests/test_agents.py, tests/test_flaky_tool.py.

**Interfaces:** ResearchAgent.run(task_id, prompt), WritingAgent.run(task_id, prompt), simulated_search_tool(task_id, query), write_workspace(task_id, data), and read_workspace(task_id) are shared by both engines.

- [x] Enforce prompt length, output schema, tool allowlist, timeouts, provider budget, and redacted error handling in deterministic code.
- [x] Route OpenAI, Anthropic, Gemini, Ollama, or offline output from settings.
- [x] Make the writer read Redis scratchpad findings and use deterministic copy when a key is absent or a key is a placeholder.
- [x] Make each task's flaky query fail once using a Redis (task_id, query) counter, then log retry and success.
- [x] Test provider adapters with fakes and test guardrail denial without network calls.

### Task 4: Temporal workflow path

**Files:** src/workflows/temporal_workflow.py, src/workflows/temporal_activities.py, src/workflows/temporal_client.py, src/worker/temporal_worker.py, tests/test_temporal_workflow.py.

**Interfaces:** HandoffWorkflow.run(task_id, prompt) uses activities mark_running, research, write_draft, await_approval, and finalize. signal_approval(task_id, approved, feedback) targets the task UUID as workflow ID.

- [x] Keep workflow code deterministic and move DB, Redis, and provider calls into retry-bounded activities.
- [x] Set RUNNING, then AWAITING_APPROVAL; wait for an approval signal; finalize to COMPLETED or REJECTED.
- [x] Use task UUID as stable workflow ID and make start/signal calls idempotent.
- [x] Test transitions and approval/rejection behavior with mocked activities or Temporal's test environment.

### Task 5: Celery bridge and Celery + LangGraph engine

**Files:** src/worker/celery_app.py, src/worker/tasks.py, src/workflows/langgraph_workflow.py, src/workflows/engine_dispatch.py, tests/test_celery_dispatch.py, tests/test_langgraph_workflow.py.

**Interfaces:** Celery tasks run_agent_workflow(task_id, prompt) and resume_agent_workflow(task_id, approved, feedback) dispatch to the selected engine. run_langgraph_phase() and resume_langgraph_phase() persist and rehydrate typed state via Redis.

- [x] Configure JSON-only serialization, late acknowledgements, reject-on-worker-loss, bounded retries, time limits, and prefetch multiplier 1.
- [x] In Temporal mode, bridge Celery start and resume messages to Temporal workflow start and approval signal.
- [x] In celery_langgraph mode, run research and writing nodes, save paused state, and resume idempotently after approval.
- [x] Test both engine selections and ensure only the selected engine executes each task.

### Task 6: Audit, log, workspace, and system-status APIs

**Files:** src/api/workspace.py, src/api/activity.py, src/api/system_status.py, src/agents/audit.py, logs/.gitkeep, tests/test_observability_api.py, tests/test_log_format.py.

- [x] Append agent_logs atomically as a JSON array and include ResearchAgent, WritingAgent, HumanApproval, and System events.
- [x] Write JSON Lines with timestamp, task_id, agent_name, and action_details to rotating file and stdout.
- [x] Implement workspace, safely tailed activity, system dependency status, and cheap /health endpoints.
- [x] Verify secrets and full prompts are absent from logs; cap activity responses at 500 lines.

### Task 7: Frontend foundation and read-only pages

**Files:** frontend/package.json, frontend/vite.config.ts, frontend/tailwind.config.ts, frontend/src/styles/tokens.css, frontend/src/App.tsx, frontend/src/router.tsx, frontend/src/api/client.ts, frontend/src/components/ui/, frontend/src/components/SiteLayout.tsx, frontend/src/pages/Landing.tsx, frontend/src/pages/History.tsx, frontend/src/pages/Architecture.tsx, frontend/src/pages/ApiReference.tsx, frontend/src/pages/SystemStatus.tsx, frontend/src/pages/NotFound.tsx.

- [x] Pin React 18 and TypeScript dependencies; bundle the chosen fonts locally.
- [x] Build accessible shadcn/ui-based button, dialog, table, textarea, and badge primitives.
- [x] Implement global navigation, route titles, skip link, error boundary, toasts, responsive states, and reduced-motion preferences.
- [x] Build landing pipeline, task history, architecture diagram, API reference, system status, and not-found page using live API data.

### Task 8: Live task detail and task submission

**Files:** frontend/src/hooks/useTaskSocket.ts, frontend/src/hooks/useTasks.ts, frontend/src/components/TaskPipeline.tsx, frontend/src/components/DraftReview.tsx, frontend/src/components/WorkspaceViewer.tsx, frontend/src/components/ActivityLog.tsx, frontend/src/pages/Console.tsx, frontend/src/pages/TaskDetail.tsx, frontend/src/pages/TaskDetail.test.tsx, frontend/src/hooks/useTaskSocket.test.ts.

- [x] Submit prompts, show a character count, and offer comparison and flaky-retry examples.
- [x] Connect WebSocket with reconnect and polling fallback; expose live connection state.
- [x] Show review, reject confirmation, workspace, audit trail, activity filter, final result copy, and Markdown download.
- [x] Test status helpers, socket fallback, and approval/rejection UI states.

### Task 9: Compose, Caddy, CI, and deployment documentation

**Files:** Dockerfile, docker-compose.yml, docker-compose.prod.yml, frontend/Dockerfile, frontend/Caddyfile, Makefile, .github/workflows/ci.yml, scripts/smoke_test.py, README.md.

- [x] Add database, Redis, API, Celery worker, Temporal development service, Temporal worker, and frontend with health dependencies.
- [x] Configure production proxying, HTTPS, persistence, restart policy, resource constraints, log rotation, and external Temporal address.
- [x] Add lint, backend tests, frontend tests/build, and Compose build to CI.
- [x] Document local lifecycle, flaky test, Redis inspection, EC2 deployment, backups, upgrades, troubleshooting, and account-dependent costs.

### Task 10: End-to-end verification and correction

**Files:** implementation files touched by failing checks and relevant tests.

- [x] Run backend tests, frontend tests, lint, type checking, and production frontend build.
- [x] Run Compose build and lifecycle smoke test if Docker is available.
- [x] Exercise both workflow engines through create, live status, approval, and completion.
- [x] Verify two flaky tasks each fail once and recover, audit entries remain ordered, and workspace exists during approval.
- [x] Record any unavailable live-provider or AWS deployment check as pending; do not invent results.

## Checkpoints

### Checkpoint A: API foundation

- [x] Schema matches exactly and creates idempotently.
- [x] API tests pass without a live provider.

### Checkpoint B: Workflow paths

- [x] Temporal and Celery + LangGraph each complete the same approval lifecycle.
- [x] Failure, retry, audit, workspace, and WebSocket assertions pass.

### Checkpoint C: Product and operations

- [x] All routes build and frontend tests pass.
- [x] Compose health checks and smoke test pass where the local environment supports Docker.
- [x] Deployment docs distinguish locally verified behavior from cloud/provider checks.

## Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Two workflow engines diverge in behavior | High | Share policy, agent, persistence, and transition services; run the same lifecycle tests against each engine. |
| Temporal server on a small EC2 instance consumes too much memory | High | Use Temporal Cloud for production deployment and document self-hosted resource requirements. |
| Provider SDKs change APIs | Medium | Pin exact versions and use provider adapters with isolated tests. |
| Provider or Temporal credentials are absent | Medium | Keep the offline path and local Temporal development service; report live checks separately. |
