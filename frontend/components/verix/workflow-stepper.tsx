import { Check, LoaderCircle, X } from "lucide-react";

import { cn } from "@/lib/utils";
import { getWorkflowSteps, type WorkflowStepEvidence } from "@/lib/repository-results";
import type { WorkflowScreen } from "@/types/workflow";

export function WorkflowStepper({ screen, evidence }: { screen: WorkflowScreen; evidence: WorkflowStepEvidence }) {
  const steps = getWorkflowSteps(screen, evidence);

  return (
    <nav
      aria-label="Verification progress"
      className="flex shrink-0 items-center overflow-x-auto border-b border-dashed border-outline-variant bg-background px-4 py-4 md:px-8"
    >
      <ol className="flex min-w-max items-center gap-2">
        {steps.map((step, index) => {
          const isCurrent = step.status === "active" || step.status === "running" || step.status === "failed";
          return (
            <li key={step.id} className="flex items-center gap-2">
              <div
                aria-current={isCurrent ? "step" : undefined}
                className={cn(
                  "flex items-center gap-2 font-heading text-xs font-bold uppercase tracking-[0.06em]",
                  step.status === "complete" && "text-success",
                  (step.status === "active" || step.status === "running") && "text-primary",
                  step.status === "failed" && "text-destructive",
                  step.status === "upcoming" && "text-muted-foreground/55",
                )}
              >
                <span
                  className={cn(
                    "flex size-5 items-center justify-center border text-[0.65rem] tabular-nums",
                    step.status === "complete" && "border-success",
                    (step.status === "active" || step.status === "running") && "border-primary",
                    step.status === "failed" && "border-destructive",
                    step.status === "upcoming" && "border-outline-variant",
                  )}
                >
                  {step.status === "complete" ? (
                    <Check className="size-3.5" aria-hidden="true" />
                  ) : step.status === "running" ? (
                    <LoaderCircle className="size-3.5 animate-spin" aria-hidden="true" />
                  ) : step.status === "failed" ? (
                    <X className="size-3.5" aria-hidden="true" />
                  ) : (
                    index + 1
                  )}
                </span>
                <span>{step.label}</span>
              </div>
              {index < steps.length - 1 && (
                <span className="h-px w-8 bg-outline-variant" aria-hidden="true" />
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
