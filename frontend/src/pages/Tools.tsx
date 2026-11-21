import { useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, ChevronDown, ExternalLink, LoaderCircle, Plus, RefreshCw, ShieldCheck, Trash2, Wrench, X } from "lucide-react";
import { api } from "../api/client";
import type { ConnectionSummary } from "../api/types";
import { PageMeta } from "../components/PageMeta";
import { Button } from "../components/ui/button";
import { useToast } from "../context/useToast";

function ConnectionCard({ connection, onRemove }: { connection: ConnectionSummary; onRemove: (id: string) => void }) {
  const [open, setOpen] = useState(false);
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const tools = useQuery({ queryKey: ["connection-tools", connection.id], queryFn: () => api.discoverTools(connection.id), enabled: open, retry: false });
  const [enabled, setEnabled] = useState(connection.enabled_tools);
  const [readOnly, setReadOnly] = useState(connection.read_only_tools);
  const [testing, setTesting] = useState(false);
  const save = useMutation({
    mutationFn: async () => {
      const discovered = tools.data ?? [];
      return api.updateConnection(connection.id, {
        name: connection.name,
        url: connection.url,
        enabled_tools: enabled.filter((name) => discovered.some((item) => item.name === name)),
        read_only_tools: readOnly.filter((name) => enabled.includes(name)),
      });
    },
    onSuccess: async () => { await queryClient.invalidateQueries({ queryKey: ["connections"] }); showToast("Tool permissions saved.", "success"); },
    onError: () => showToast("Could not save tool permissions.", "error"),
  });

  async function test() {
    setTesting(true);
    try {
      const result = await api.testConnection(connection.id);
      showToast(result.ok ? `Connection works · ${result.tool_count ?? 0} tools found.` : `Connection check failed (${result.error ?? "unknown error"}).`, result.ok ? "success" : "error");
    } catch { showToast("Connection check failed.", "error"); }
    finally { setTesting(false); }
  }
  function toggle(list: string[], setter: (value: string[]) => void, name: string) {
    setter(list.includes(name) ? list.filter((item) => item !== name) : [...list, name]);
  }

  return (
    <article className="connection-card">
      <div className="connection-header"><span className="connection-icon"><Wrench size={18} /></span><div className="connection-main"><strong>{connection.name}</strong><a href={connection.url} target="_blank" rel="noreferrer">{connection.url}<ExternalLink size={12} /></a></div><span className="connection-tool-count">{connection.enabled_tools.length} enabled</span><button className="icon-button" onClick={() => setOpen((value) => !value)} aria-expanded={open} aria-label={open ? "Hide tools" : "Configure tools"}>{open ? <X size={17} /> : <ChevronDown size={17} />}</button></div>
      {open && <div className="connection-details">
        <div className="tool-list-heading"><div><strong>Available tools</strong><p>Only selected tools are offered to the research agent.</p></div><Button variant="secondary" size="small" onClick={() => void tools.refetch()} disabled={tools.isFetching}>{tools.isFetching ? <LoaderCircle className="spin" size={14} /> : <RefreshCw size={14} />}Refresh</Button></div>
        {tools.isLoading || tools.isFetching ? <div className="loading-line" /> : tools.isError ? <div className="inline-error">Could not reach this MCP server. Check the URL and credentials.</div> : tools.data?.length ? <div className="remote-tool-list">{tools.data.map((tool) => <div className="remote-tool" key={tool.name}>
          <label className="tool-toggle"><input type="checkbox" checked={enabled.includes(tool.name)} onChange={() => toggle(enabled, setEnabled, tool.name)} /><span className="toggle-mark"><Check size={12} /></span><span><strong>{tool.name}</strong><small>{tool.description || "No description provided."}</small></span></label>
          {enabled.includes(tool.name) && <label className="readonly-toggle"><input type="checkbox" checked={readOnly.includes(tool.name)} onChange={() => toggle(readOnly, setReadOnly, tool.name)} /><ShieldCheck size={14} />Treat as read-only</label>}
          {enabled.includes(tool.name) && !readOnly.includes(tool.name) && <span className="approval-note">Each call waits for your approval</span>}
        </div>)}</div> : <p className="empty-state">No tools were advertised by this server.</p>}
        <div className="connection-actions"><Button variant="secondary" size="small" onClick={() => void test()} disabled={testing}>{testing ? <LoaderCircle className="spin" size={14} /> : <RefreshCw size={14} />}Test connection</Button><Button size="small" onClick={() => save.mutate()} disabled={save.isPending}>{save.isPending ? <LoaderCircle className="spin" size={14} /> : <Check size={14} />}Save permissions</Button><Button variant="quiet" size="small" onClick={() => onRemove(connection.id)}><Trash2 size={14} />Remove</Button></div>
      </div>}
    </article>
  );
}

export function Tools() {
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [url, setUrl] = useState("");
  const [token, setToken] = useState("");
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const connections = useQuery({ queryKey: ["connections"], queryFn: api.listConnections });
  const create = useMutation({
    mutationFn: () => api.createConnection({ name: name.trim(), url: url.trim(), bearer_token: token || undefined, enabled_tools: [], read_only_tools: [] }),
    onSuccess: async () => { setName(""); setUrl(""); setToken(""); setShowForm(false); await queryClient.invalidateQueries({ queryKey: ["connections"] }); showToast("Connection added. Discover its tools to configure access.", "success"); },
    onError: () => showToast("Could not add this connection. Use an HTTPS URL on a public host.", "error"),
  });
  const remove = useMutation({
    mutationFn: api.deleteConnection,
    onSuccess: async () => { await queryClient.invalidateQueries({ queryKey: ["connections"] }); showToast("Connection removed.", "success"); },
    onError: () => showToast("Could not remove this connection.", "error"),
  });

  function submit(event: FormEvent<HTMLFormElement>) { event.preventDefault(); create.mutate(); }

  return (
    <main id="main" className="page-wrap">
      <PageMeta title="Tool connections" description="Connect MCP servers and decide which tools the research agent can use." />
      <div className="page-heading page-heading-action"><div><p className="eyebrow">CONNECTED TOOLS</p><h1>Tools for your research</h1><p>Add an MCP server, choose the tools Handoff may call, and mark only trusted tools as read-only.</p></div><Button onClick={() => setShowForm((value) => !value)}>{showForm ? <X size={16} /> : <Plus size={16} />}{showForm ? "Close" : "Add connection"}</Button></div>
      <div className="tool-safety-note"><ShieldCheck size={17} /><p>Tool connections belong to your account. Calls not marked read-only pause for your approval before they run.</p></div>
      {showForm && <form className="connection-form" onSubmit={submit}>
        <div className="section-title"><div><h2>New MCP connection</h2><p>Use an HTTPS Streamable HTTP endpoint that you trust.</p></div></div>
        <div className="form-grid"><label className="field-label">Connection name<input value={name} onChange={(event) => setName(event.target.value)} maxLength={120} required placeholder="Notion workspace" /></label><label className="field-label">Server URL<input type="url" value={url} onChange={(event) => setUrl(event.target.value)} required placeholder="https://tools.example.com/mcp" /></label><label className="field-label form-wide">Bearer token <span className="muted">optional</span><input type="password" value={token} onChange={(event) => setToken(event.target.value)} autoComplete="new-password" placeholder="Stored encrypted · never returned" /></label></div>
        <div className="connection-actions"><Button type="button" variant="secondary" onClick={() => setShowForm(false)}>Cancel</Button><Button type="submit" disabled={create.isPending}>{create.isPending ? <LoaderCircle className="spin" size={15} /> : <Plus size={15} />}Add server</Button></div>
      </form>}
      <section className="connections-list">
        {connections.isLoading ? <div className="loading-line" /> : connections.isError ? <div className="inline-error">Could not load your connections.</div> : connections.data?.length ? connections.data.map((connection) => <ConnectionCard key={connection.id} connection={connection} onRemove={(id) => remove.mutate(id)} />) : <div className="connections-empty"><div className="empty-icon"><Wrench size={18} /></div><strong>No tool connections yet</strong><p>Connect an MCP server to make its approved tools available to your research runs.</p><Button variant="secondary" size="small" onClick={() => setShowForm(true)}><Plus size={14} />Add a connection</Button></div>}
      </section>
    </main>
  );
}
