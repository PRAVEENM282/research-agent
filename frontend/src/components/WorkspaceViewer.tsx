import { useState } from "react";
import { Check, Copy, Database } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";

export function WorkspaceViewer({ taskId }: { taskId: string }) {
  const [copied, setCopied] = useState(false);
  const workspace = useQuery({ queryKey: ["workspace", taskId], queryFn: () => api.getWorkspace(taskId), retry: false });
  const copy = async () => {
    if (!workspace.data) return;
    await navigator.clipboard.writeText(JSON.stringify(workspace.data.workspace, null, 2));
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1_500);
  };
  return (
    <section className="surface surface-pad" aria-labelledby="workspace-title">
      <div className="section-title">
        <h2 id="workspace-title"><Database size={18} /> Shared workspace</h2>
        {workspace.data && <button className="text-action" onClick={() => void copy()}>{copied ? <Check size={15} /> : <Copy size={15} />}{copied ? "Copied" : "Copy JSON"}</button>}
      </div>
      {workspace.isLoading ? <div className="loading-line" /> : workspace.data ? <pre className="code-block workspace-json">{JSON.stringify(workspace.data.workspace, null, 2)}</pre> : workspace.error ? <p className="muted workspace-empty">Workspace expired or has not been written yet.</p> : null}
    </section>
  );
}
