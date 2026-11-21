import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, LoaderCircle, ShieldAlert, X } from "lucide-react";
import { api } from "../api/client";
import { Button } from "./ui/button";
import { useToast } from "../context/useToast";

export function ToolCallReview({ taskId }: { taskId: string }) {
  const approvals = useQuery({ queryKey: ["tool-approvals", taskId], queryFn: () => api.listToolApprovals(taskId), refetchInterval: 5_000 });
  const client = useQueryClient();
  const { showToast } = useToast();
  const decide = useMutation({
    mutationFn: ({ callId, approved }: { callId: string; approved: boolean }) => api.decideToolApproval(taskId, callId, approved),
    onSuccess: async (_, values) => {
      await Promise.all([
        client.invalidateQueries({ queryKey: ["tool-approvals", taskId] }),
        client.invalidateQueries({ queryKey: ["task", taskId] }),
      ]);
      showToast(values.approved ? "Tool call approved. Research will resume." : "Tool call denied. Research will resume without it.", values.approved ? "success" : "info");
    },
    onError: () => showToast("Could not save the tool decision.", "error"),
  });
  const pending = approvals.data?.filter((item) => item.status === "PENDING_APPROVAL") ?? [];
  if (approvals.isLoading || !pending.length) return null;
  return <section className="tool-review-list" aria-label="Tool approval requests">{pending.map((item) => <article className="tool-review-card" key={item.call_id}>
    <div className="tool-review-title"><span className="approval-icon"><ShieldAlert size={17} /></span><div><p className="eyebrow">YOUR APPROVAL NEEDED</p><h2>{item.tool_name}</h2></div></div>
    <p>This connected tool may change data outside Handoff. Review the arguments before allowing it to run.</p>
    <pre className="arguments-preview">{JSON.stringify(item.arguments, null, 2)}</pre>
    <div className="approval-actions"><Button variant="secondary" size="small" disabled={decide.isPending} onClick={() => decide.mutate({ callId: item.call_id, approved: false })}><X size={15} />Deny</Button><Button size="small" disabled={decide.isPending} onClick={() => decide.mutate({ callId: item.call_id, approved: true })}>{decide.isPending ? <LoaderCircle className="spin" size={15} /> : <Check size={15} />}Approve tool call</Button></div>
  </article>)}</section>;
}
