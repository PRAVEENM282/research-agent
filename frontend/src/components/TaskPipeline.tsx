import { Check, Circle, FileSearch, PenLine, ShieldCheck, UserRound } from "lucide-react";
import type { TaskStatus } from "../api/types";
import { getPipelineStep } from "./taskPipelineStep";

const steps = [
  { id: "research", label: "Research", icon: FileSearch },
  { id: "writing", label: "Writing", icon: PenLine },
  { id: "review", label: "Human review", icon: UserRound },
  { id: "complete", label: "Finished", icon: ShieldCheck },
];

export function TaskPipeline({ status, animate = false }: { status: TaskStatus; animate?: boolean }) {
  const active = getPipelineStep(status);
  const failed = status === "FAILED" || status === "REJECTED";
  return (
    <ol className={`pipeline ${animate ? "pipeline-animate" : ""}`} aria-label={`Task workflow, current status ${status.toLowerCase().replaceAll("_", " ")}`}>
      {steps.map((step, index) => {
        const Icon = step.icon;
        const done = active > index;
        const current = active === index;
        const isHuman = step.id === "review";
        const className = `pipeline-step ${done ? "is-done" : ""} ${current ? "is-current" : ""} ${isHuman && status === "AWAITING_APPROVAL" ? "is-human-wait" : ""} ${failed && current ? "is-failed" : ""}`;
        return (
          <li className={className} key={step.id}>
            <span className="pipeline-marker" aria-hidden="true">{done ? <Check size={17} /> : current ? <Icon size={17} /> : <Circle size={13} />}</span>
            <span className="pipeline-label">{step.label}</span>
            {index < steps.length - 1 && <span className="pipeline-connector" aria-hidden="true" />}
          </li>
        );
      })}
    </ol>
  );
}
