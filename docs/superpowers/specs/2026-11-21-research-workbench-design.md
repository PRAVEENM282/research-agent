# Handoff Research Workbench Design

**Date:** 2026-11-21  
**Status:** Proposed for user review

## Objective

Make Handoff a trustworthy research workbench. A user can sign in, start research, see the work and sources that support an answer, connect permitted tools, and review a draft before it is finalized. The application must not imply that a mock search, offline writer, or unmeasured evaluation is live AI research.

The redesign covers three connected workstreams:

1. OIDC identity and private per-user task access.
2. Real web research, provider-neutral tool execution, xAI support, and MCP connections.
3. A task-first frontend, useful documentation, and settings.

Temporal remains the primary workflow engine. Celery + LangGraph remains available as the secondary configured engine.

## Product direction

Handoff is a research and approval workbench, not a general agent canvas or an evaluation dashboard. Product references informed the run-detail experience: traces show tool use and retrieved context; quality, cost, latency, and user feedback are meaningful only when measured; navigation should keep attention on the active work. Handoff will surface its actual run evidence and feedback without introducing unimplemented datasets or fabricated scores.

### Considered approaches

- **Research workbench (chosen):** Put research creation, runs, tool connections, documentation, and settings around a run detail view. This matches the current product and exposes missing research evidence directly.
- **Evaluation console:** Add datasets, experiments, scorers, and comparisons. This needs an evaluation storage and execution system that does not exist, so it is a separate future product phase.
- **Minimal task tracker:** Keep only a landing page, run list, documentation, and settings. This is smaller but leaves tool configuration and source inspection without a clear home.

## Information architecture

### Routes

- `/` — concise public landing page for signed-out visitors; signed-in users continue to `/workspace`.
- `/login` — OIDC sign-in.
- `/workspace` — real recent runs and drafts awaiting the user's decision, with a prominent Start research action.
- `/runs` — searchable, filterable run history.
- `/runs/:id` — task lifecycle, tool calls, retries, source evidence, draft/final answer, and approval controls.
- `/tools` — configured search/extraction tools and MCP connections, with scoped tool permissions.
- `/docs` — getting started, providers and tools, authentication, API reference, WebSocket events, and error responses.
- `/settings` — account and profile preferences, active provider configuration state, and connection preferences.

Architecture and Status are removed from product navigation. The API reference becomes a section of Documentation. FastAPI's interactive schema page moves to `/api/reference`; the raw OpenAPI document remains at `/openapi.json`. This avoids the current Caddy/Vite `/docs` proxy collision and lets `/docs` become the product documentation route. Legacy `/api` navigation redirects to `/docs#api`; the health endpoint remains for deployment probes, not as an application page.

### Desktop and mobile layout

The signed-in shell fills the viewport instead of centering a narrow 1,180 px site column. Desktop uses a compact, approximately 220 px navigation rail and a fluid work area with 24–32 px gutters. Run detail uses a broad report column and a contextual source panel; the report text itself remains a readable line length. At mobile widths, the rail becomes a menu and source details open in a drawer. No content is hidden behind decorative whitespace or repeated identical cards.

The visual system keeps Handoff's cool mineral surface and dark teal ink, uses blue only for active agent work, ochre for a pending human decision, and green for completed work. Borders and spacing carry hierarchy; shadows and gradients are reserved for no essential content. Fira Sans and Fira Mono remain bundled locally. Motion is limited to feedback for user actions or real run-state changes and respects reduced-motion settings.

The signature interaction is a run trace with meaningful steps—research, extraction, writing, and human review—paired with the evidence those steps produced. Source rows show the original URL, title, retrieval time, and a bounded excerpt. Each citation in a final answer opens the matching source. Failed and empty states explain the next useful action.

## Identity, privacy, and API access

Use configurable OIDC with Authorization Code + PKCE, validated issuer metadata, state and nonce checks, and an HttpOnly, Secure, SameSite=Lax session cookie. The frontend never receives the client secret. Provider and callback settings come from environment configuration. The operator can restrict sign-in to an email allowlist or explicitly enable registration for every verified account at the configured issuer. Both modes retain per-user data isolation.

Require CSRF protection on state-changing cookie-authenticated requests and validate same-origin requests. WebSocket upgrades validate the Origin and require an authenticated session. Logout invalidates the server-side session and clears the cookie.

Create a user identity record keyed by OIDC issuer and subject, and a separate task-owner mapping so the existing `tasks` table contract does not need to change. Every task, workspace, activity, approval, and WebSocket operation checks ownership. New runs are private to their creator. MCP connection records and credentials are scoped to that same user.

Existing tasks have no owner. They remain invisible to every account until an operator sets an explicit `OIDC_BOOTSTRAP_EMAIL`. After that email completes verified OIDC sign-in, Handoff assigns the unowned tasks to the authenticated `(issuer, subject)` in the same transaction as session creation. This avoids requiring an operator to discover the provider's opaque subject in advance; unowned rows never appear in normal task queries. Open registration does not change ownership of existing tasks.

The documentation describes same-origin session authentication for the web client and exact API behavior. It does not claim that unauthenticated task endpoints remain available. API tokens are not part of this design; they can be added later if external automation needs a non-browser credential flow. Settings reports the environment-managed provider and model plus whether credentials are configured; it never returns key values and does not pretend to edit the server's `.env` file.

## Research and tool execution

### Real search and extraction

Replace the fixed `simulated_search_tool` path with a research tool registry. The user's prompt is the search intent; the system may derive bounded subqueries, but it never substitutes a fixed LangGraph/CrewAI query. The self-hostable default is SearXNG for result discovery and Trafilatura for static-page extraction. Search and extraction are separate steps. Crawl4AI is an optional, explicitly configured browser fallback for JavaScript-heavy pages; it is not enabled by default because it adds a browser runtime and memory cost to the EC2 deployment.

Search limits, fetch timeouts, maximum redirects, result count, page count, extracted bytes, and per-host rate limits are configured and enforced by the application. Fetches accept public HTTP/HTTPS URLs only. Resolve and re-check addresses on redirects, blocking loopback, private, link-local, and cloud metadata ranges. Do not bypass authentication, paywalls, CAPTCHAs, or site access controls. Fail with a clear task error when live search is not configured or unavailable; never return fixture findings as if they were live.

Redis remains the short-lived workflow scratchpad. Persist source metadata and bounded excerpts in a task-linked Postgres artifact table so citations survive Redis expiry and remain isolated by owner. Do not persist full scraped pages by default.

### Provider-neutral tools, xAI, and MCP

Add xAI as an explicit LLM provider configured through environment variables, alongside OpenAI, Anthropic, Gemini, and Ollama. Model-visible tools use a provider-neutral name, description, and JSON Schema. The worker validates every requested call against the user's allowed tool set, input schema, maximum call count, timeout, and output size before execution. Results are returned to the selected provider through its supported tool-call format. Provider failures are logged with safe error categories; keys, raw provider bodies, and full prompts are not logged.

Handoff executes configured MCP tools on the application side. This lets Grok and other providers use the same guarded tool registry without requiring the model provider to reach a private Handoff deployment. MCP server URLs must use HTTPS outside local development. Only explicitly allowlisted tools are exposed. Read-only tools are the default; side-effecting tools require a human approval checkpoint before execution. Per-user connection secrets are write-only in the UI and encrypted at rest with a server-managed key.

The workflow records provider, model, tool name, bounded timing, success/failure, and source references for inspection. The deterministic offline writer remains available but is labeled as offline in the run. It cannot turn mock findings into live research.

## Frontend components and content

Keep the existing React/Vite/Tailwind 3 and Radix/shadcn source components as the foundation. Use those accessible primitives for navigation, dialogs, forms, tables, and menus. Build focused Handoff components for the run trace, source evidence, tool events, and approval decision rather than installing a chat-centric UI kit or migrating the whole frontend to a different React/Tailwind generation.

Documentation is organized for a user completing a task: sign in and configure a provider; start a research run; inspect sources and approve a draft; connect an MCP server; then use the API. The API reference includes authenticated curl examples, request and response schemas, status transitions, pagination/filter rules, rate limits, error bodies, and WebSocket setup. Link the interactive schema and raw OpenAPI file as secondary references.

## Delivery sequence

1. **Identity and data boundary:** add OIDC configuration/callback/session handling, user and ownership records, safe migration for legacy tasks, and ownership checks across REST and WebSocket APIs.
2. **Research runtime:** add durable source artifacts, SearXNG search, Trafilatura extraction, URL/network limits, xAI provider support, provider-neutral tool calls, and guarded MCP connections.
3. **Product surface:** replace current navigation/pages with the workbench routes; add run evidence and connection views; provide the documentation hub and accurate API schema paths; remove Architecture and Status UI.
4. **Deployment and operations:** document OIDC, SearXNG, provider, MCP encryption, and resource configuration; update Compose/Caddy; verify isolated accounts, real-source citations, approval behavior, and both workflow engines.

## Acceptance criteria

- A submitted prompt drives live search queries; no hard-coded demo research result is used in a normal run.
- A completed answer has source citations tied to durable, task-owned metadata and bounded extracted excerpts.
- Unconfigured or failed search and provider paths report their actual state; they do not silently present offline or fixture output as live research.
- xAI can request allowlisted Handoff tools; tool calls are validated and recorded. MCP connections are scoped, encrypted, and subject to read-only/approval policy.
- OIDC-protected API, task, approval, and WebSocket routes enforce private per-user ownership.
- Legacy tasks are assigned only through the explicit bootstrap-owner migration.
- The app has no Architecture or Status navigation/page; `/docs` is the product documentation route and interactive API docs use `/api/reference`.
- The workspace uses available desktop width, remains usable at 320 px, supports keyboard navigation and visible focus, and honors reduced motion.
- UI quality indicators are based on recorded run data and user feedback. No fabricated benchmark, quality, cost, or latency score is shown.
- Temporal remains the default workflow engine and the Celery + LangGraph path retains equivalent task and approval behavior.

## Out of scope

- Dataset management, offline evaluation suites, model leaderboard, or LLM-judge scores.
- Browser automation as the default scraping path.
- Automatically granting write-capable tools or letting a model approve its own action.
- A public status dashboard or architecture diagram page.
- Promise of zero-cost AWS operation; SearXNG and the existing workflow services consume instance resources, and account eligibility and resource fit must be checked during deployment.

## Design review

- The design keeps task evidence at the center rather than adding a generic analytics dashboard.
- It distinguishes search discovery from page extraction and reserves browser-based crawling for a configured fallback.
- It changes `/docs` ownership deliberately because the current proxy sends `/docs` to FastAPI, while the redesigned product needs `/docs` for its user guide.
- It requires authorized OIDC identities and CSRF protection for cookie-authenticated mutations.
- It does not add an unsupported API-token flow; browser auth is documented as OIDC-backed session auth.
- It preserves workflow-engine choices from the original platform design while adding per-user authorization that the old design explicitly lacked.
