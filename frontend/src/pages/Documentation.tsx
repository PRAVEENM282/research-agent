import { BookOpen, ExternalLink, Fingerprint, KeyRound, MessageSquareMore, Search, Wrench } from "lucide-react";
import { PageMeta } from "../components/PageMeta";

const endpoints = [
  { method: "GET", path: "/api/v1/auth/me", purpose: "Resolve the signed-in account and return the CSRF token." },
  { method: "GET", path: "/api/v1/tasks", purpose: "List only research runs owned by your account." },
  { method: "POST", path: "/api/v1/tasks", purpose: "Create a private research run from a prompt." },
  { method: "GET", path: "/api/v1/tasks/{id}/sources", purpose: "Read the source records saved for a run." },
  { method: "POST", path: "/api/v1/tasks/{id}/approve", purpose: "Approve or reject a completed draft." },
  { method: "POST", path: "/api/v1/tasks/{id}/tool-approvals/{call_id}", purpose: "Allow or deny a requested side-effecting tool call." },
];

export function Documentation() {
  return (
    <main id="main" className="page-wrap">
      <PageMeta title="Documentation" description="Practical guide to Handoff research runs, evidence, sessions, and tools." />
      <div className="page-heading"><p className="eyebrow">GUIDE</p><h1>Documentation</h1><p>How to start a run, review its evidence, and connect guarded tools.</p></div>
      <div className="docs-layout">
        <nav className="docs-toc" aria-label="On this page"><span>ON THIS PAGE</span><a href="#runs">Research runs</a><a href="#evidence">Sources and citations</a><a href="#tools">Connected tools</a><a href="#auth">Sessions and security</a><a href="#api">API reference</a></nav>
        <div className="docs-body">
          <section id="runs" className="docs-section"><span className="docs-icon"><Search size={17} /></span><div><h2>Research runs</h2><p>Write a specific brief with the question, audience, and kind of answer you need. Handoff sends the brief to live search, extracts a bounded set of public pages, saves the sources with the run, and prepares a draft for your review.</p><p>If search or page extraction fails, the run reports the failure. When no language model is configured, Handoff labels the result as offline synthesis and shows retrieved excerpts instead of presenting a canned answer as AI work.</p></div></section>
          <section id="evidence" className="docs-section"><span className="docs-icon"><BookOpen size={17} /></span><div><h2>Sources and citations</h2><p>Open a run’s Sources panel to see the URL, retrieval time, extraction status, and text excerpt. Generated answers cite those source URLs. Source pages are untrusted input; instructions found inside a page do not grant tools or change approval rules.</p></div></section>
          <section id="tools" className="docs-section"><span className="docs-icon"><Wrench size={17} /></span><div><h2>Connected tools</h2><p>Add an MCP Streamable HTTP server using HTTPS. Discover the server’s tool list, then explicitly enable tools for your account. Handoff treats a tool as read-only only when you mark it that way in the connection settings.</p><p>Other calls pause and show the bounded arguments for your approval. If a remote call times out after execution may have started, Handoff marks its outcome indeterminate and does not retry it automatically.</p></div></section>
          <section id="auth" className="docs-section"><span className="docs-icon"><Fingerprint size={17} /></span><div><h2>Sessions and security</h2><p>Sign-in uses your configured OpenID Connect provider. Handoff keeps the durable session in an HttpOnly cookie, restricts access to the configured verified-email allowlist, and scopes runs and connections to the signed-in account.</p><p>State-changing API requests require the CSRF token returned by <code>GET /api/v1/auth/me</code> in the <code>X-CSRF-Token</code> header. Use the same origin as the web application.</p></div></section>
          <section id="api" className="docs-section docs-api-section"><span className="docs-icon"><MessageSquareMore size={17} /></span><div><h2>API reference</h2><p>Interactive OpenAPI reference, schema download, and common endpoints.</p><div className="docs-links"><a href="/api/reference" target="_blank" rel="noreferrer"><KeyRound size={15} />Open API reference <ExternalLink size={13} /></a><a href="/openapi.json" target="_blank" rel="noreferrer">Download OpenAPI JSON <ExternalLink size={13} /></a></div>
            <div className="endpoint-list">{endpoints.map((endpoint) => <div className="endpoint-row" key={`${endpoint.method}-${endpoint.path}`}><span className={`endpoint-method method-${endpoint.method.toLowerCase()}`}>{endpoint.method}</span><code>{endpoint.path}</code><p>{endpoint.purpose}</p></div>)}</div>
            <pre className="code-block"><code>{`const session = await fetch("/api/v1/auth/me").then(r => r.json());
const response = await fetch("/api/v1/tasks", {
  method: "POST",
  credentials: "same-origin",
  headers: {
    "Content-Type": "application/json",
    "X-CSRF-Token": session.csrf_token
  },
  body: JSON.stringify({ prompt: "Research the question…" })
});`}</code></pre>
          </div></section>
        </div>
      </div>
    </main>
  );
}
