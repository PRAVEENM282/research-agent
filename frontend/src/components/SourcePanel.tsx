import { useQuery } from "@tanstack/react-query";
import { ArrowUpRight, BookOpen, Clock3, FileWarning } from "lucide-react";
import { api } from "../api/client";

export function SourcePanel({ taskId }: { taskId: string }) {
  const sources = useQuery({ queryKey: ["sources", taskId], queryFn: () => api.getSources(taskId) });
  return (
    <section className="evidence-panel" aria-labelledby="sources-heading">
      <div className="panel-heading"><div><p className="eyebrow">EVIDENCE</p><h2 id="sources-heading">Sources</h2></div><span className="evidence-count">{sources.data?.sources.length ?? 0}</span></div>
      {sources.isLoading ? <div className="source-loading"><div className="loading-line" /><div className="loading-line" /></div> : sources.isError ? <p className="muted small-copy">Sources will appear after live search.</p> : sources.data?.sources.length ? <div className="source-list">{sources.data.sources.map((source, index) => <article className="source-card" key={source.id}>
        <div className="source-card-top"><span className="source-number">{String(index + 1).padStart(2, "0")}</span><span className={`source-status ${source.status.toLowerCase()}`}>{source.status === "EXTRACTED" ? <BookOpen size={12} /> : <FileWarning size={12} />}{source.status === "EXTRACTED" ? "Extracted" : "Unavailable"}</span></div>
        <a href={source.url} target="_blank" rel="noreferrer" className="source-title">{source.title}<ArrowUpRight size={14} /></a>
        <div className="source-meta"><span>{source.domain}</span><span><Clock3 size={12} />{new Date(source.retrieved_at).toLocaleString()}</span></div>
        {source.excerpt && <p className="source-excerpt">{source.excerpt}</p>}
      </article>)}</div> : <div className="sources-empty"><BookOpen size={18} /><p>Retrieved sources will be attached here.</p></div>}
    </section>
  );
}
