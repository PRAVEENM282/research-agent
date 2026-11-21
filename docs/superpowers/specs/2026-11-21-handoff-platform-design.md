# Handoff Platform Design

**Date:** 2026-11-21  
**Status:** Approved by the user

## Objective

Build Handoff as a deployable multi-agent workflow console. Users submit a prompt, watch research and writing agents collaborate, inspect the shared workspace and audit trail, review a draft, and approve or reject it. The API stays responsive while work runs asynchronously.

## Architecture

PostgreSQL is the source of truth for task records. Redis holds the agent workspace, workflow-engine selection, retry counters, rate-limit state, and short-lived status events. FastAPI owns REST and WebSocket contracts. A Celery worker is the asynchronous dispatch bridge.

Each task runs on exactly one configured engine:

- WORKFLOW_ENGINE=temporal is the default. The Celery bridge starts or signals a Temporal workflow. A Temporal worker runs research and writing activities, waits durably for approval, and finalizes the result.
- WORKFLOW_ENGINE=celery_langgraph runs the typed LangGraph in Celery. The first run writes the draft and paused graph state to Redis; approval dispatches a resume task that rehydrates it and completes the graph. Finished nodes are idempotent when re-entered.

The API conditionally moves an awaiting task to RESUMED, appends the human decision, publishes the status, and dispatches the resume bridge task. The Temporal workflow ID and Celery task ID derive from the task UUID. A Redis engine key preserves which engine owns a task through approval and retry.

Both engines share agent activities, provider adapter, Redis scratchpad, status transitions, policy checks, logging, and task persistence. Provider calls happen only in worker activities or tasks. Workflow code owns state transitions and approval; the model cannot grant approval or choose unbounded tools.

## Data and contracts

The tasks table follows the supplied seven-column contract exactly. API requests validate prompts to 1–4000 characters. Create returns HTTP 202 with a UUID and PENDING. Unknown tasks return 404, invalid UUIDs return 422, and invalid approval states return 409. Rejection ends in REJECTED; approval resumes and ends in COMPLETED. Errors end in FAILED with a safe user-facing reason.

Required task, approval, list, workspace, activity, status, health, and WebSocket endpoints use one JSON error shape. WebSocket clients receive the current database status immediately, then Redis-published transitions until a terminal status or disconnect.

## Agent policy and reliability

Input and output size limits, validated structured responses, tool allowlists, provider timeouts and budgets, idempotent task IDs, and deterministic approval checks enforce policy in application code. Prompt text, provider responses, and tool results remain untrusted data. Logs redact keys and avoid full prompts. The mock research tool returns fixed facts and stores scratchpad data at task:<id>:workspace; the writer reads that Redis value. The flaky-test attempt counter is scoped to (task_id, query) in Redis and expires.

OpenAI, Anthropic, Gemini, and Ollama are selected through environment configuration. Empty or placeholder API keys use a deterministic offline writer. External provider failures retry with bounded backoff and then mark the task failed.

## Frontend design

The experience is a calm control room organized around task handoffs. Palette: mineral #EDF0EE, ink teal #10282C, agent blue #2D46D6, human amber #E39A12, completion green #1F8A5B, and failure red #C43D3D. These colors encode status. Fira Sans carries interface and headline text; Fira Mono is reserved for code, JSON, and logs. Both are bundled locally under the SIL Open Font License. This revised the first type choice to use a locally available, redistributable family and preserve deterministic loading without a third-party font request.

The landing hero is a live handoff pipeline. It plays one short sequence, stops at the human gate, and honors reduced-motion preferences. Task detail places the current pipeline above the draft or final result, review controls, scratchpad, audit trail, and activity log. A 12-column desktop grid collapses into a single-column flow at narrow widths; reading copy stays below 80 characters per line. Spacing, alignment, and a small number of state-bearing dividers carry the hierarchy. shadcn/ui primitives are used selectively for accessible buttons, dialogs, tables, and textareas; the pipeline and task visualizations are custom.

The landing page, console, task detail, history, architecture, API reference, system status, and not-found pages use the real API. Focus visibility, semantic HTML, keyboard operation, WCAG AA contrast, 360px responsiveness, reduced motion, and loading/error/empty states are required. The hero animation is the only ambient motion; other motion accompanies status or user actions.

## Deployment

Docker Compose includes PostgreSQL, Redis, API, Celery bridge, Temporal development server, Temporal worker, and Caddy-served frontend. The production override accepts an external production Temporal endpoint (recommended Temporal Cloud) and publishes only the web proxy on 80/443. Production requires explicit secrets, HTTPS, restart/resource/log limits, persistent volumes, backup instructions, and no source mounts.

The EC2 guide documents Docker deployment, DNS, TLS, backups, upgrades, and cost controls. Free Tier eligibility and credits depend on AWS account age and plan; the project does not promise that a multi-container production stack runs at zero cost. Temporal's local dev server is for local development; production connects to Temporal Cloud or an independently operated production Temporal service.

## Design review

The first design pass used the suggested semantic palette and a pipeline-led hero. Review preserved the state semantics but removed generic dashboard decoration: no gradient wash, no repeated card grid, no all-caps eyebrows, and no animation on every section. The signature element remains the route and pause point of a real task.

## Acceptance

- Both workflow engines can complete research, draft, approval, resume, and completion using the same API contract.
- Retry, audit, scratchpad, status, and WebSocket behaviors are inspectable.
- A new developer can start the local stack from .env.example, run tests, and follow a documented EC2 deployment path.
- The frontend is responsive, accessible, and integrated with the backend.
