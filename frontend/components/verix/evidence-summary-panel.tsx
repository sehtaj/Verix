import {
  AlertTriangle,
  CheckCircle2,
  CircleDashed,
  Lightbulb,
  ShieldAlert,
  XCircle,
} from "lucide-react";

import type { EvidenceSummary } from "@/types/api";


const assessmentPresentation = {
  observed_failures: {
    label: "Failures observed",
    className: "border-destructive bg-destructive/5 text-destructive",
    Icon: XCircle,
  },
  incomplete: {
    label: "Evidence incomplete",
    className: "border-primary bg-primary/5 text-primary",
    Icon: AlertTriangle,
  },
  no_observed_failures: {
    label: "No failures observed",
    className: "border-success bg-success/5 text-success",
    Icon: CheckCircle2,
  },
};

export function EvidenceSummaryPanel({ summary }: { summary: EvidenceSummary }) {
  const assessment = assessmentPresentation[summary.assessment];
  const AssessmentIcon = assessment.Icon;

  return (
    <section className="mt-5 border border-outline-variant bg-surface">
      <header className="flex flex-col gap-3 border-b border-dashed border-outline-variant bg-surface-high p-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="font-heading text-sm font-bold uppercase">Evidence Summary</h2>
          <p className="mt-1 text-xs text-muted-foreground">
            Deterministic facts from this run, not an AI conclusion.
          </p>
        </div>
        <div className={`flex items-center gap-2 border px-3 py-2 font-heading text-xs uppercase ${assessment.className}`}>
          <AssessmentIcon className="size-4" aria-hidden="true" />
          {assessment.label}
        </div>
      </header>

      <div className="grid gap-px bg-outline-variant md:grid-cols-2 xl:grid-cols-4">
        <EvidenceBucket
          title="Passed"
          items={summary.passed}
          empty="No passing evidence was recorded."
          className="text-success"
          Icon={CheckCircle2}
        />
        <EvidenceBucket
          title="Failed"
          items={summary.failed}
          empty="No failures were observed."
          className="text-destructive"
          Icon={XCircle}
        />
        <EvidenceBucket
          title="Assumed"
          items={summary.assumed}
          empty="No explicit AI assumptions were recorded."
          className="text-primary"
          Icon={Lightbulb}
        />
        <EvidenceBucket
          title="Untested"
          items={summary.untested}
          empty="No known evidence gaps were recorded."
          className="text-muted-foreground"
          Icon={CircleDashed}
        />
      </div>

      <div className="border-t border-dashed border-outline-variant p-4">
        <p className="font-heading text-[10px] uppercase text-muted-foreground">Expected-behavior sources</p>
        <ul className="mt-2 flex flex-wrap gap-2">
          {summary.behavior_sources.map((source, index) => (
            <li key={`${source.kind}:${source.path}:${index}`} className="path-text border border-outline-variant px-2 py-1 text-xs">
              {source.kind.replaceAll("_", " ")} · {source.path}
            </li>
          ))}
        </ul>
        <p className="mt-4 flex items-start gap-2 border border-dashed border-outline-variant bg-surface-low p-3 text-xs text-muted-foreground">
          <ShieldAlert className="mt-0.5 size-4 shrink-0 text-primary" aria-hidden="true" />
          {summary.disclaimer}
        </p>
      </div>
    </section>
  );
}

type EvidenceBucketProps = {
  title: string;
  items: string[];
  empty: string;
  className: string;
  Icon: typeof CheckCircle2;
};

function EvidenceBucket({ title, items, empty, className, Icon }: EvidenceBucketProps) {
  return (
    <section className="bg-surface p-4">
      <h3 className={`flex items-center gap-2 font-heading text-xs font-bold uppercase ${className}`}>
        <Icon className="size-4" aria-hidden="true" /> {title}
      </h3>
      {items.length ? (
        <ul className="mt-3 space-y-2 text-xs text-foreground">
          {items.map((item) => <li key={item} className="border-l border-current/40 pl-2">{item}</li>)}
        </ul>
      ) : (
        <p className="mt-3 text-xs text-muted-foreground">{empty}</p>
      )}
    </section>
  );
}
