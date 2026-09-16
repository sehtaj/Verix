"use client";

import { FlaskConical, RefreshCw, Search, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  CodeEvidence,
  ExecutionEvidence,
  PreparationEvidence,
} from "@/components/verix/execution-evidence";
import { getExecutionStatus } from "@/lib/repository-results";
import { GeneratedTestReportPanel } from "@/components/verix/generated-test-report";
import type { RepositoryGenerationRun } from "@/types/api";

type GenerationResultPanelProps = {
  result: RepositoryGenerationRun;
  error: string | null;
  isActionBusy?: boolean;
  onRegenerate: () => void;
  onInvestigate: () => void;
};

export function GenerationResultPanel({
  result,
  error,
  isActionBusy = false,
  onRegenerate,
  onInvestigate,
}: GenerationResultPanelProps) {
  const generatedStatus = getExecutionStatus(result.generated_execution);
  const generatedPassed = generatedStatus === "passed";

  return (
    <section className="mx-auto w-full max-w-5xl">
      <header className="mb-6">
        <div className="flex items-center gap-3 text-primary">
          <Sparkles className="size-8" aria-hidden="true" />
          <h1 className="text-balance font-heading text-3xl font-bold">
            Focused Tests Generated
          </h1>
        </div>
        <p className="mt-2 text-muted-foreground">
          Generated code and execution evidence remain separate from the repository&apos;s own suite.
        </p>
      </header>

      <dl className="mb-5 grid gap-px border border-outline-variant bg-outline-variant sm:grid-cols-[1fr_auto]">
        <div className="min-w-0 bg-surface-low p-3">
          <dt className="font-heading text-[10px] uppercase text-muted-foreground">Pinned Target</dt>
          <dd className="path-text mt-1 font-heading text-sm text-primary">{result.target_path}</dd>
        </div>
        <div className="bg-surface-low p-3">
          <dt className="font-heading text-[10px] uppercase text-muted-foreground">Runner</dt>
          <dd className="mt-1 font-heading text-sm uppercase">{result.test_runner}</dd>
        </div>
      </dl>

      <CodeEvidence title="Generated Pytest Code" code={result.generated_tests} />
      <GeneratedTestReportPanel report={result.generated_test_report} />

      <div className="mt-5 space-y-4">
        <PreparationEvidence preparation={result.preparation} />
        <ExecutionEvidence
          title="Dependency Installation"
          execution={result.installation}
          defaultExpanded={getExecutionStatus(result.installation) !== "passed"}
        />
      </div>

      <section className="mt-5 grid gap-5 lg:grid-cols-2" aria-label="Separated test evidence">
        <div className="space-y-3 border border-dashed border-outline-variant bg-surface p-4">
          <h2 className="flex items-center gap-2 font-heading text-sm font-bold uppercase">
            <FlaskConical className="size-4 text-muted-foreground" aria-hidden="true" />
            Existing Test Evidence
          </h2>
          <p className="text-xs text-muted-foreground">
            Results from the repository&apos;s original suite. Absence is not treated as a pass.
          </p>
          <ExecutionEvidence
            title="Existing Tests"
            execution={result.existing_execution}
            defaultExpanded={getExecutionStatus(result.existing_execution) !== "passed"}
          />
        </div>

        <div className="space-y-3 border border-primary/70 bg-surface p-4">
          <h2 className="flex items-center gap-2 font-heading text-sm font-bold uppercase text-primary">
            <Sparkles className="size-4" aria-hidden="true" />
            Generated Test Evidence
          </h2>
          <p className="text-xs text-muted-foreground">
            Results from the newly generated focused suite for the selected target.
          </p>
          <ExecutionEvidence
            title="Generated Tests"
            execution={result.generated_execution}
            defaultExpanded={!generatedPassed}
          />
        </div>
      </section>

      {error && (
        <p className="mt-5 border border-destructive bg-destructive/10 p-3 text-sm text-destructive" role="alert">
          {error}
        </p>
      )}

      <footer className="mt-6 flex flex-wrap gap-3 border border-dashed border-outline-variant bg-surface-low p-4">
        <Button variant="outline" disabled={isActionBusy} onClick={onRegenerate}>
          <RefreshCw /> Regenerate Focused Tests
        </Button>
        <Button disabled={isActionBusy} onClick={onInvestigate}>
          <Search /> Investigate Complete Evidence
        </Button>
      </footer>
    </section>
  );
}
