import type { AuditEntry } from "../api/types";
import { Clock3 } from "lucide-react";

export function RunTrace({ entries }: { entries: AuditEntry[] }) {
  if (!entries.length) return <p className="muted small-copy">Run events will appear here.</p>;
  return <ol className="run-trace">{entries.map((entry, index) => <li key={`${entry.timestamp}-${index}`}>
    <span className={`trace-marker ${entry.agent === "HumanApproval" ? "trace-human" : entry.agent === "System" ? "trace-system" : "trace-agent"}`} />
    <div><div className="trace-heading"><strong>{entry.agent}</strong><time dateTime={entry.timestamp}><Clock3 size={11} />{new Date(entry.timestamp).toLocaleString()}</time></div><p>{entry.action}</p></div>
  </li>)}</ol>;
}
