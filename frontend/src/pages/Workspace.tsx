import { useState, type FormEvent } from "react";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight, LoaderCircle, Search, Sparkles } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { ApiError } from "../api/types";
import { PageMeta } from "../components/PageMeta";
import { Button } from "../components/ui/button";
import { Textarea } from "../components/ui/textarea";
import { useToast } from "../context/useToast";

export function Workspace() {
  const [prompt, setPrompt] = useState("");
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();
  const { showToast } = useToast();
  const recent = useQuery({ queryKey: ["tasks", "recent"], queryFn: () => api.listTasks({ limit: 6 }), refetchInterval: 10_000 });

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!prompt.trim() || busy) return;
    setBusy(true);
    try {
      const task = await api.createTask(prompt.trim());
      navigate(`/tasks/${task.task_id}`);
    } catch (error) {
      showToast(error instanceof ApiError ? error.message : "Could not start this research run.", "error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main id="main" className="page-wrap">
      <PageMeta title="Workspace" description="Start a private, source-led research run." />
      <section className="workspace-intro"><div><p className="eyebrow">RESEARCH WORKSPACE</p><h1>What do you need to know?</h1><p>Describe the question and the answer you need. Handoff will search for sources, build a cited draft, and ask you to review it.</p></div><div className="intro-mark"><Sparkles size={22} /></div></section>
      <div className="workspace-grid">
        <form className="composer-card" onSubmit={(event) => void submit(event)}>
          <label htmlFor="research-prompt" className="field-label">Research brief</label>
          <Textarea id="research-prompt" value={prompt} onChange={(event) => setPrompt(event.target.value.slice(0, 4000))} maxLength={4000} rows={7} required placeholder="For example: Compare the latest approaches to evaluating browser agents. Cite primary sources and summarize where the methods differ." />
          <div className="composer-footer"><span className="character-count">{prompt.length.toLocaleString()} / 4,000</span><Button type="submit" disabled={!prompt.trim() || busy}>{busy ? <LoaderCircle className="spin" size={16} /> : <Search size={16} />}{busy ? "Starting research" : "Start research"}<ArrowRight size={16} /></Button></div>
          <div className="composer-hint"><span className="hint-dot" />Runs are private to your account. Side-effecting connected tools wait for your approval.</div>
        </form>

        <section className="recent-panel" aria-labelledby="recent-heading">
          <div className="panel-heading"><div><p className="eyebrow">RECENT</p><h2 id="recent-heading">Your research runs</h2></div><Link to="/tasks" className="text-action">See all <ArrowRight size={14} /></Link></div>
          <div className="run-list">
            {recent.isLoading ? <div className="run-loading"><div className="loading-line" /><div className="loading-line" /><div className="loading-line" /></div> : recent.data?.items.length ? recent.data.items.map((task) => <Link to={`/tasks/${task.id}`} className="run-row" key={task.id}><span className={`run-state state-${task.status.toLowerCase()}`} aria-hidden="true" /><span className="run-copy"><strong>{task.prompt}</strong><small>{new Date(task.created_at).toLocaleString()}</small></span><span className="run-status">{task.status === "AWAITING_APPROVAL" ? "Review" : task.status === "AWAITING_TOOL_APPROVAL" ? "Tool approval" : task.status === "COMPLETED" ? "Complete" : task.status === "FAILED" ? "Failed" : "In progress"}</span></Link>) : <div className="runs-empty"><div className="empty-icon"><Search size={19} /></div><strong>Your first research run starts here.</strong><p>Runs and their sources will appear in this list.</p></div>}
          </div>
        </section>
      </div>
    </main>
  );
}
