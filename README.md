# Handoff

Handoff is a private research workbench. A research run searches the live web, extracts a bounded set of public pages, stores source records, drafts an answer with citations, and waits for your review before completion. Each person sees only the runs and MCP connections they own.

## Start locally

Requirements: Docker Engine and Docker Compose v2.

```sh
cp .env.example .env
chmod 600 .env
```

For the simplest personal setup, use Google as the OIDC provider. GitHub OAuth Apps do not issue OIDC ID tokens, so they cannot be used directly with this sign-in flow.

1. In [Google Cloud Console](https://console.cloud.google.com/), create or select a project, set up the Google Auth Platform consent screen, and create a **Web application** OAuth client.
2. Add this exact authorized redirect URI to the client: `http://localhost/api/v1/auth/callback`.
3. If the audience is External and the app is in Testing, add your Google account under Test users.
4. Copy the client ID and client secret into the server `.env` file. The secret stays on the server and is never sent to the browser.

Set these `.env` values:

```env
OIDC_ISSUER_URL=https://accounts.google.com
OIDC_CLIENT_ID=your-web-client-id
OIDC_CLIENT_SECRET=your-web-client-secret
OIDC_REDIRECT_URI=http://localhost/api/v1/auth/callback
OIDC_ALLOWED_EMAILS=
OIDC_ALLOW_ANY_EMAILS=true
OIDC_BOOTSTRAP_EMAIL=you@example.com
```

`OIDC_ALLOW_ANY_EMAILS=true` allows any Google account with a verified email to create its own Handoff account. Each account still sees only its own runs and tool connections. Leave it `false` and set `OIDC_ALLOWED_EMAILS` to keep sign-in restricted. Set `OIDC_BOOTSTRAP_EMAIL` to the account that should inherit old unowned runs; only that verified identity receives them. The app's session and encryption keys are already generated in the local `.env`; keep that file private.

Then start the application:

```sh
docker compose up --build
```

Open [http://localhost](http://localhost) for local development. Handoff itself is available at `/`; the product guide is at `/docs`, and the interactive OpenAPI reference is at `/api/reference`. Production uses HTTPS through Caddy when configured with a real domain.

The local stack includes PostgreSQL, Redis, API and Celery services, Temporal's development server and worker, SearXNG, and Caddy. SearXNG JSON results are enabled in `deploy/searxng/settings.yml`. Local research pages are fetched with a public-address check, a pinned destination IP, redirect revalidation, response-size limits, and Trafilatura extraction.

If old tasks exist, set `OIDC_BOOTSTRAP_EMAIL` to the account that should own them. Those tasks stay inaccessible until that account completes verified OIDC sign-in; Handoff then assigns unowned runs to that authenticated identity in the same database transaction. You do not need to find the provider's opaque `sub` value. Leave this setting empty for a fresh database.

## Providers and research

Set `LLM_PROVIDER` and `LLM_MODEL` in `.env`. Supported values are `openai`, `xai`, `anthropic`, `gemini`, and `ollama`. OpenAI-compatible keys use `LLM_API_KEY`; xAI uses `XAI_API_KEY`. Ollama uses `LLM_BASE_URL` and a model already available to that service. Restart API and worker services after changing provider environment values.

An empty or placeholder hosted-provider key selects an explicitly labeled offline synthesis. Web search and page extraction still run, and the result contains retrieved source excerpts. A configured provider failure is reported as a failed run; Handoff does not substitute fixture facts. Live search requires the configured SearXNG service.

Search, extraction, redirects, fetch time, page bytes, results, and tool calls are bounded by `RESEARCH_MAX_*` settings. Only public HTTP and HTTPS pages on standard ports can be fetched. Optional JavaScript crawling is not enabled by default.

## Connect MCP tools

Open **Tool connections**, add an HTTPS Streamable HTTP endpoint, and discover its tools. Enable only the tools you want to offer to the research agent. Mark a tool read-only only if you trust it not to change external state. Other calls wait for your approval and show their bounded, redacted arguments first.

Connection bearer tokens and pending tool arguments are encrypted at rest using `APP_ENCRYPTION_KEY`. Credentials are never returned to the browser. If an approved remote call times out after it might have started, Handoff records an indeterminate result and will not retry that side effect automatically.

## Workflow engines

Temporal is the primary engine. The local Compose stack uses Temporal's development server. For a production deployment, set `TEMPORAL_ADDRESS`, `TEMPORAL_NAMESPACE`, and `TEMPORAL_API_KEY` for a production Temporal endpoint and start the `temporal-worker` profile.

`WORKFLOW_ENGINE=celery_langgraph` selects the supported Celery + LangGraph workflow. It uses persisted Redis state for both draft approval and MCP tool approval. New runs capture the selected engine when they are created.

## API and sessions

The browser signs in through OIDC. API sessions use an HttpOnly cookie and owner-scoped database queries. Sign-in can be restricted with an email allowlist or opened to all verified accounts at the configured issuer. State-changing requests require the `X-CSRF-Token` returned by `GET /api/v1/auth/me`, plus a same-origin `Origin` header. Do not call protected task or connection APIs with anonymous `curl` requests.

Key endpoints:

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/api/v1/auth/me` | Current user and CSRF token |
| `GET` | `/api/v1/tasks` | List the signed-in user's runs |
| `POST` | `/api/v1/tasks` | Create a research run |
| `GET` | `/api/v1/tasks/{id}/sources` | Read saved source records |
| `POST` | `/api/v1/tasks/{id}/approve` | Approve or reject a draft |
| `POST` | `/api/v1/tasks/{id}/tool-approvals/{call_id}` | Approve or deny a mutating tool call |

`GET /health` is the unauthenticated liveness probe. There is no user-facing architecture or system-status page.

## Production on EC2

The production Compose override serves the UI through Caddy, keeps the API port private, uses named log volumes, and applies container resource and log limits. Before deployment:

1. Check the current AWS account's Free Tier eligibility and memory capacity. The full stack includes database, Redis, search, API, Celery, and a Temporal worker; a micro instance may not have enough memory. AWS charges depend on the account, instance, storage, traffic, and external model or Temporal services, so this setup does not promise a zero bill.
2. Point a DNS name at the instance and allow inbound 80/443 for Caddy certificate issuance. Restrict SSH to your operator IP. Do not publish PostgreSQL, Redis, SearXNG, Temporal, or port 8000 publicly.
3. Set `DOMAIN`, `ENVIRONMENT=production`, and `SESSION_COOKIE_SECURE=true`. Set the OIDC issuer/client settings, a verified email allowlist, `OIDC_REDIRECT_URI=https://YOUR_DOMAIN/api/v1/auth/callback`, `OIDC_SESSION_SECRET`, `APP_ENCRYPTION_KEY`, and a private PostgreSQL password in `.env`.
4. Set `TEMPORAL_ADDRESS`, `TEMPORAL_NAMESPACE`, and `TEMPORAL_API_KEY` for the production Temporal service. The local Temporal development server is disabled in the production override.
5. Keep `.env` readable only by the deployment user, then start the services:

   ```sh
   chmod 600 .env
   docker compose -f docker-compose.yml -f docker-compose.prod.yml --profile temporal up -d --build
   ```

Visit `https://YOUR_DOMAIN`. Back up PostgreSQL off-instance and test restores before relying on those backups. Keep encrypted copies of deployment secrets outside the host. Review `docker compose ps` and the service logs during rollout.

