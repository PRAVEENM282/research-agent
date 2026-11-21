import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import ReactMarkdown from "react-markdown";
import { ArrowDownToLine, ArrowLeft, Check, Copy, MessageCircle, RotateCw } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import { ApiError } from "../api/types";
import { ActivityLog } from "../components/ActivityLog";
import { DraftReview } from "../components/DraftReview";
import { PageMeta } from "../components/PageMeta";
import { RunTrace } from "../components/RunTrace";
import { SourcePanel } from "../components/SourcePanel";
import { ToolCallReview } from "../components/ToolCallReview";
import { StatusBadge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { useToast } from "../context/useToast";
import { useTask } from "../hooks/useTasks";
import { useTaskSocket } from "../hooks/useTaskSocket";

const stages = ["Research", "Draft", "Review", "Complete"];

function stageIndex(status: string) {
  if (["PENDING", "RUNNING", "AWAITING_TOOL_APPROVAL"].includes(status)) return 0;
  if (status === "AWAITING_APPROVAL") return 2;
  if (["RESUMED", "COMPLETED"].includes(status)) return 3;
  return 1;
}

export function TaskDetail() {
  const { id } = useParams<{ id: string }>();
  const task = useTask(id);
  const connection = useTaskSocket(id);
  const client = useQueryClient();
  const { showToast } = useToast();
  const [copied, setCopied] = useState(false);
  const review = useMutation({
    mutationFn: ({ approved, feedback }: { approved: boolean; feedback: string }) => api.approveTask(id!, approved, feedback),
    onSuccess: async (response) => {
      await Promise.all([client.invalidateQueries({ queryKey: ["task", id] }), client.invalidateQueries({ queryKey: ["tasks"] })]);
      showToast(response.status === "RESUMED" ? "Draft approved. Saving the final answer." : "Draft rejected.", response.status === "RESUMED" ? "success" : "info");
    },
    onError: (error) => showToast(error instanceof ApiError ? error.message : "The review decision could not be saved.", "error"),
  });
  const feedback = useMutation({
    mutationFn: (rating: "helpful" | "unhelpful") => api.submitFeedback(id!, rating),
    onSuccess: () => showToast("Thanks for the feedback.", "success"),
    onError: () => showToast("Feedback could not be saved.", "error"),
  });

  async function copyResult() {
    if (!task.data?.result) return;
    await navigator.clipboard.writeText(task.data.result);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1200);
  }
  function downloadResult() {
    if (!task.data?.result) return;
    const url = URL.createObjectURL(new Blob([`# ${task.data.prompt}\n\n${task.data.result}\n`], { type: "text/markdown;charset=utf-8" }));
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `handoff-${task.data.id}.md`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  if (task.isLoading) return <main id="main" className="page-wrap"><div className="loading-line" /><div className="loading-line" /></main>;
  if (task.error || !task.data) {
    const missing = task.error instanceof ApiError && task.error.status === 404;
    return <main id="main" className="page-wrap"><PageMeta title="Run unavailable" description="This research run could not be loaded." /><section className="error-card"><h1>{missing ? "Run not found" : "Could not load this run"}</h1><p>{missing ? "This run is unavailable or does not belong to your account." : task.error instanceof Error ? task.error.message : "Try again in a moment."}</p><Link className="button button-secondary" to="/tasks"><ArrowLeft size={15} />Research runs</Link></section></main>;
  }

  const record = task.data;
  const running = ["PENDING", "RUNNING", "RESUMED"].includes(record.status);
  const progress = stageIndex(record.status);
  const statusHeading: Record<string, string> = {
    PENDING: "Queued for research",
    RUNNING: "Research is underway",
    AWAITING_TOOL_APPROVAL: "A connected tool needs your approval",
    AWAITING_APPROVAL: "Review the draft before it is finalized",
    RESUMED: "Saving your approved answer",
    COMPLETED: "Research complete",
    FAILED: "This run stopped",
    REJECTED: "Draft rejected",
  };
  return (
    <main id="main" className="page-wrap run-detail">
      <PageMeta title="Research run" description="Review a research answer alongside its sources and run history." />
      <Link className="back-link" to="/tasks"><ArrowLeft size={14} />Research runs</Link>
      <header className="run-detail-heading"><div><p className="eyebrow">RESEARCH BRIEF</p><h1>{record.prompt}</h1><p className="run-created">Started {new Date(record.created_at).toLocaleString()}</p></div><StatusBadge status={record.status} /></header>
      <section className="run-progress" aria-label="Research progress">
        <div className="progress-title"><div><span className={`progress-orb ${running ? "orb-active" : ""}`} /><div><p className="eyebrow">RUN PROGRESS</p><h2>{statusHeading[record.status] ?? "Research run"}</h2></div></div><span className={`socket-label socket-${connection}`}>{connection === "live" ? "Live updates" : connection === "polling" ? "Reconnecting" : connection === "closed" ? "Finished" : "Connecting"}</span></div>
        <ol className="progress-steps">{stages.map((stage, index) => <li className={`${index < progress ? "step-done" : ""} ${index === progress ? "step-current" : ""}`} key={stage}><span>{index < progress ? <Check size={13} /> : String(index + 1).padStart(2, "0")}</span>{stage}</li>)}</ol>
      </section>
      <ToolCallReview taskId={record.id} />
      {record.status === "AWAITING_APPROVAL" && record.result && <DraftReview draft={record.result} busy={review.isPending} onApprove={(note) => review.mutate({ approved: true, feedback: note })} onReject={(note) => review.mutate({ approved: false, feedback: note })} />}
      {record.status === "COMPLETED" && record.result && <section className="answer-panel">
        <div className="answer-heading"><div><p className="eyebrow">FINAL ANSWER</p><h2>Research summary</h2></div><div className="answer-actions"><Button size="small" variant="secondary" onClick={() => void copyResult()}>{copied ? <Check size={14} /> : <Copy size={14} />}{copied ? "Copied" : "Copy"}</Button><Button size="small" variant="secondary" onClick={downloadResult}><ArrowDownToLine size={14} />Export</Button></div></div>
        <div className="markdown-body"><ReactMarkdown>{record.result}</ReactMarkdown></div>
        <div className="answer-feedback"><span><MessageCircle size={14} />Was this useful?</span><Button size="small" variant="quiet" disabled={feedback.isPending} onClick={() => feedback.mutate("helpful")}>Yes</Button><Button size="small" variant="quiet" disabled={feedback.isPending} onClick={() => feedback.mutate("unhelpful")}>Not quite</Button></div>
      </section>}
      {record.status === "FAILED" && <div className="run-failure" role="alert"><strong>Research did not finish</strong><p>{record.result ?? "Check the run events and service configuration, then start a new run."}</p></div>}
      {record.status === "REJECTED" && record.result && <section className="answer-panel"><p className="eyebrow">REJECTED DRAFT</p><div className="markdown-body"><ReactMarkdown>{record.result}</ReactMarkdown></div></section>}
      {running && record.result && <section className="answer-panel"><div className="answer-heading"><div><p className="eyebrow">DRAFT</p><h2>Work in progress</h2></div><RotateCw size={16} className="muted" /></div><div className="markdown-body"><ReactMarkdown>{record.result}</ReactMarkdown></div></section>}
      <div className="run-detail-grid"><SourcePanel taskId={record.id} /><section className="evidence-panel"><div className="panel-heading"><div><p className="eyebrow">PROCESS</p><h2>Run history</h2></div></div><RunTrace entries={record.agent_logs ?? []} /></section></div>
      <details className="activity-disclosure"><summary>Detailed activity</summary><ActivityLog taskId={record.id} /></details>
    </main>
  );
}
