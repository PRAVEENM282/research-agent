import { useMemo, useState } from "react";
import { useTasks } from "../hooks/useTasks";
import { Link } from "react-router-dom";
import { ArrowLeft, ArrowRight, Search } from "lucide-react";
import { PageMeta } from "../components/PageMeta";
import { StatusBadge } from "../components/ui/badge";
import { Button } from "../components/ui/button";

const filters = [
  ["All runs", ""],
  ["In progress", "RUNNING"],
  ["Review needed", "AWAITING_APPROVAL"],
  ["Tool approval", "AWAITING_TOOL_APPROVAL"],
  ["Complete", "COMPLETED"],
  ["Failed", "FAILED"],
];

export function History() {
  const [status, setStatus] = useState("");
  const [search, setSearch] = useState("");
  const [offset, setOffset] = useState(0);
  const limit = 20;
  const query = useTasks(status || undefined, limit, offset);
  const items = useMemo(() => (query.data?.items ?? []).filter((task) => task.prompt.toLowerCase().includes(search.toLowerCase())), [query.data, search]);
  const total = query.data?.total ?? 0;
  return (
    <main id="main" className="page-wrap">
      <PageMeta title="Research runs" description="Search and open your private Handoff research runs." />
      <div className="page-heading"><p className="eyebrow">YOUR WORK</p><h1>Research runs</h1><p>Find a previous brief, review its sources, or continue a pending decision.</p></div>
      <section className="history-panel">
        <div className="history-controls"><label className="history-search"><Search size={16} /><span className="sr-only">Search briefs</span><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search briefs" /></label><label className="history-filter"><span className="sr-only">Filter runs</span><select value={status} onChange={(event) => { setStatus(event.target.value); setOffset(0); }}>{filters.map(([label, value]) => <option value={value} key={value}>{label}</option>)}</select></label></div>
        {query.isLoading ? <div className="history-loading"><div className="loading-line" /><div className="loading-line" /></div> : items.length ? <div className="history-list">{items.map((task) => <Link to={`/tasks/${task.id}`} className="history-row" key={task.id}><span className={`run-state state-${task.status.toLowerCase()}`} /><span className="history-run-copy"><strong>{task.prompt}</strong><small>{new Date(task.created_at).toLocaleString()}</small></span><StatusBadge status={task.status} /><ArrowRight className="history-arrow" size={16} /></Link>)}</div> : <div className="runs-empty"><div className="empty-icon"><Search size={18} /></div><strong>{search || status ? "No matching runs" : "No research runs yet"}</strong><p>{search || status ? "Try a different search or filter." : "Start from your workspace and your runs will collect here."}</p>{!search && !status && <Link className="text-action" to="/workspace">Start research <ArrowRight size={14} /></Link>}</div>}
        <footer className="history-footer"><span>{total ? `${offset + 1}–${Math.min(offset + limit, total)} of ${total}` : ""}</span><div><Button variant="secondary" size="small" disabled={!offset} onClick={() => setOffset(Math.max(0, offset - limit))}><ArrowLeft size={14} />Previous</Button><Button variant="secondary" size="small" disabled={offset + limit >= total} onClick={() => setOffset(offset + limit)}>Next<ArrowRight size={14} /></Button></div></footer>
      </section>
    </main>
  );
}
