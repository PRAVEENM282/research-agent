import { useState } from "react";
import ReactMarkdown from "react-markdown";
import { Check, CircleAlert, X } from "lucide-react";
import { Button } from "./ui/button";
import { Textarea } from "./ui/textarea";
import { Dialog } from "./ui/dialog";

export function DraftReview({ draft, busy, onApprove, onReject }: {
  draft: string;
  busy: boolean;
  onApprove: (feedback: string) => void;
  onReject: (feedback: string) => void;
}) {
  const [feedback, setFeedback] = useState("");
  const [confirmReject, setConfirmReject] = useState(false);
  return (
    <section className="surface surface-pad review-panel" aria-labelledby="draft-heading">
      <div className="review-heading">
        <div><p className="eyebrow">Human review</p><h2 id="draft-heading">Review draft</h2></div>
        <span className="review-mark"><CircleAlert size={17} /> Decision required</span>
      </div>
      <div className="markdown-body draft-body"><ReactMarkdown>{draft}</ReactMarkdown></div>
      <label className="field-label" htmlFor="review-feedback">Feedback for the final version <span className="muted">optional</span></label>
      <Textarea id="review-feedback" value={feedback} onChange={(event) => setFeedback(event.target.value)} maxLength={2000} rows={3} placeholder="Add a note for the writing agent…" />
      <div className="review-actions">
        <Button disabled={busy} onClick={() => onApprove(feedback)}><Check size={17} />Approve and finish</Button>
        <Button variant="secondary" disabled={busy} onClick={() => setConfirmReject(true)}><X size={17} />Reject draft</Button>
      </div>
      <Dialog open={confirmReject} onOpenChange={setConfirmReject} title="Reject this draft?" description="This task will stop with a rejected status. The draft and review note remain in its history.">
        <div className="dialog-actions">
          <Button variant="secondary" onClick={() => setConfirmReject(false)}>Keep reviewing</Button>
          <Button variant="danger" disabled={busy} onClick={() => { setConfirmReject(false); onReject(feedback); }}>Reject draft</Button>
        </div>
      </Dialog>
    </section>
  );
}
