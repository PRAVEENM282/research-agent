import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Activity, Filter } from "lucide-react";
import { api } from "../api/client";
import type { ActivityEntry } from "../api/types";

const tones = (entry: ActivityEntry) => /failed|error/i.test(entry.action_details) ? "activity-failure" : /retry/i.test(entry.action_details) ? "activity-retry" : /completed|succeeded/i.test(entry.action_details) ? "activity-success" : "";

export function ActivityLog({ taskId }: { taskId: string }) {
  const [agent, setAgent] = useState("all");
  const activity = useQuery({ queryKey: ["activity", taskId], queryFn: () => api.getActivity(taskId), refetchInterval: 4_000 });
  const agents = useMemo(() => [...new Set(activity.data?.entries.map((entry) => entry.agent_name) ?? [])], [activity.data]);
  const entries = (activity.data?.entries ?? []).filter((entry) => agent === "all" || entry.agent_name === agent);
  return (
    <section className="surface surface-pad" aria-labelledby="activity-title">
      <div className="section-title">
        <h2 id="activity-title"><Activity size={18} /> Activity</h2>
        <label className="filter-control"><Filter size={15} /><span className="sr-only">Filter activity by agent</span><select value={agent} onChange={(event) => setAgent(event.target.value)}><option value="all">All agents</option>{agents.map((name) => <option key={name}>{name}</option>)}</select></label>
      </div>
      {activity.isLoading ? <div className="loading-line" /> : entries.length ? (
        <ol className="activity-list">
          {entries.map((entry, index) => <li className={`activity-row ${tones(entry)}`} key={`${entry.timestamp}-${index}`}><time className="activity-time" dateTime={entry.timestamp}>{new Date(entry.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}</time><span className="activity-agent">{entry.agent_name}</span><span className="activity-detail">{entry.action_details}</span></li>)}
        </ol>
      ) : <p className="empty-state">Activity will appear as the task moves through its steps.</p>}
    </section>
  );
}
