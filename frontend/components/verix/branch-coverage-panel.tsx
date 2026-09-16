import { Activity, AlertTriangle } from "lucide-react";

import type { BranchCoverageSummary } from "@/types/api";


export function BranchCoveragePanel({ coverage }: { coverage: BranchCoverageSummary }) {
  if (!coverage.available || !coverage.existing || !coverage.combined) {
    return (
      <section className="mt-5 border border-dashed border-outline-variant bg-surface-low p-4">
        <h2 className="flex items-center gap-2 font-heading text-xs font-bold uppercase text-muted-foreground">
          <AlertTriangle className="size-4 text-primary" aria-hidden="true" /> Branch Coverage Unavailable
        </h2>
        <p className="mt-2 text-sm text-muted-foreground">{coverage.unavailable_reason}</p>
      </section>
    );
  }

  return (
    <section className="mt-5 border border-dashed border-outline-variant bg-surface-low p-4">
      <header>
        <h2 className="flex items-center gap-2 font-heading text-xs font-bold uppercase text-primary">
          <Activity className="size-4" aria-hidden="true" /> Selected-Source Branch Coverage
        </h2>
        <p className="path-text mt-2 text-xs text-muted-foreground">{coverage.target_path}</p>
      </header>
      <dl className="mt-4 grid gap-px border border-outline-variant bg-outline-variant sm:grid-cols-4">
        <CoverageValue
          label="Existing suite"
          value={`${coverage.existing.covered_branches}/${coverage.existing.total_branches}`}
          detail={`${coverage.existing.percent.toFixed(1)}%`}
        />
        <CoverageValue
          label="Combined"
          value={`${coverage.combined.covered_branches}/${coverage.combined.total_branches}`}
          detail={`${coverage.combined.percent.toFixed(1)}%`}
        />
        <CoverageValue
          label="Generated delta"
          value={`+${coverage.incremental_covered_branches}`}
          detail="new branches"
        />
        <CoverageValue
          label="Still untested"
          value={String(coverage.untested_branches)}
          detail="branches"
        />
      </dl>
      <p className="mt-3 text-xs text-muted-foreground">
        Coverage shows which branches executed; it does not prove the assertions or behavior are correct.
      </p>
    </section>
  );
}

function CoverageValue({ label, value, detail }: { label: string; value: string; detail: string }) {
  return (
    <div className="bg-surface p-3">
      <dt className="font-heading text-[10px] uppercase text-muted-foreground">{label}</dt>
      <dd className="mt-1 font-heading text-xl font-bold tabular-nums text-foreground">{value}</dd>
      <dd className="mt-1 text-xs text-muted-foreground">{detail}</dd>
    </div>
  );
}
