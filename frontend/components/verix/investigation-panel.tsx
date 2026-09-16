"use client";

import {
  AlertTriangle,
  CheckCircle2,
  FileSearch,
  RefreshCw,
  ShieldAlert,
  Wrench,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  CodeEvidence,
  ExecutionEvidence,
  PreparationEvidence,
} from "@/components/verix/execution-evidence";
import { getExecutionStatus, getOutcomeLabel } from "@/lib/repository-results";
import { GeneratedTestReportPanel } from "@/components/verix/generated-test-report";
import { BranchCoveragePanel } from "@/components/verix/branch-coverage-panel";
import type { RepositoryInvestigationRun } from "@/types/api";

type InvestigationPanelProps = {
  result: RepositoryInvestigationRun;
  error: string | null;
  isActionBusy?: boolean;
  onRetry: () => void;
  onProposeFix: () => void;
  onEditRepository: () => void;
};

const fixEligibleOutcomes = new Set<RepositoryInvestigationRun["investigation"]["outcome"]>([
  "existing_tests_timed_out",
  "existing_tests_failed",
  "generated_tests_timed_out",
  "generated_tests_failed",
]);

const failureOutcomes = new Set<RepositoryInvestigationRun["investigation"]["outcome"]>([
  "setup_failed",
  "existing_tests_timed_out",
  "existing_tests_failed",
  "generated_tests_timed_out",
  "generated_tests_failed",
]);

export function InvestigationPanel({
  result,
  error,
  isActionBusy = false,
  onRetry,
  onProposeFix,
  onEditRepository,
}: InvestigationPanelProps) {
  const passed = result.investigation.outcome === "tests_passed";
  const failed = failureOutcomes.has(result.investigation.outcome);
  const canProposeFix = fixEligibleOutcomes.has(result.investigation.outcome);
  const OutcomeIcon = passed ? CheckCircle2 : AlertTriangle;

  return (
    <section className="mx-auto w-full max-w-5xl">
      <header>
        <div className={`flex items-center gap-3 ${passed ? "text-success" : failed ? "text-destructive" : "text-primary"}`}>
          <FileSearch className="size-8" aria-hidden="true" />
          <h1 className="text-balance font-heading text-3xl font-bold">Investigation Evidence</h1>
        </div>
        <p className="mt-2 text-muted-foreground">
          Verix performed a fresh bounded generation-and-run pass for the pinned source target.
        </p>
      </header>

      <section className={`mt-6 border p-5 ${passed ? "border-success bg-success/5" : failed ? "border-destructive bg-destructive/5" : "border-primary bg-primary/5"}`}>
        <div className="flex items-start gap-3">
          <OutcomeIcon className="mt-0.5 size-6 shrink-0" aria-hidden="true" />
          <div>
            <p className="font-heading text-xs uppercase tracking-[0.12em] text-muted-foreground">Authoritative Outcome</p>
            <h2 className="mt-1 font-heading text-xl font-bold">{getOutcomeLabel(result.investigation.outcome)}</h2>
            <p className="mt-3 max-w-3xl break-words text-foreground">{result.investigation.explanation}</p>
          </div>
        </div>
      </section>

      <div className="mt-5 space-y-4">
        <PreparationEvidence preparation={result.preparation} />
        <ExecutionEvidence
          title="Dependency Installation"
          execution={result.installation}
          defaultExpanded={getExecutionStatus(result.installation) !== "passed"}
        />
      </div>

      <section className="mt-5 grid gap-5 lg:grid-cols-2" aria-label="Investigation execution evidence">
        <div className="space-y-3 border border-dashed border-outline-variant bg-surface p-4">
          <h2 className="font-heading text-sm font-bold uppercase">Existing Tests</h2>
          <ExecutionEvidence
            title={`Original Suite · ${result.test_runner}`}
            execution={result.existing_execution}
            defaultExpanded={getExecutionStatus(result.existing_execution) !== "passed"}
          />
        </div>
        <div className="space-y-3 border border-dashed border-primary/70 bg-surface p-4">
          <h2 className="font-heading text-sm font-bold uppercase text-primary">Generated Tests</h2>
          <ExecutionEvidence
            title={`Focused Suite · ${result.test_runner}`}
            execution={result.generated_execution}
            defaultExpanded={getExecutionStatus(result.generated_execution) !== "passed"}
          />
        </div>
      </section>

      <BranchCoveragePanel coverage={result.branch_coverage} />

      <div className="mt-5">
        <CodeEvidence title="Generated Investigation Tests" code={result.generated_tests} />
      </div>
      <GeneratedTestReportPanel report={result.generated_test_report} />

      <section className="mt-5 border border-dashed border-outline-variant bg-surface-low p-4">
        <h2 className="font-heading text-xs font-bold uppercase text-muted-foreground">Detected Test Plan</h2>
        <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div className="border border-dashed border-outline-variant p-3 text-sm">
            <span className="text-muted-foreground">Project tool:</span>{" "}
            {result.test_plan.setup.project_tool ?? "Not detected"}
          </div>
          <div className="border border-dashed border-outline-variant p-3 text-sm">
            <span className="text-muted-foreground">Test runner:</span>{" "}
            {result.test_plan.setup.test_runner ?? result.test_runner}
          </div>
          <div className="border border-dashed border-outline-variant p-3 text-sm">
            <span className="text-muted-foreground">Source files:</span>{" "}
            {result.test_plan.source_paths.length}
          </div>
          <div className="border border-dashed border-outline-variant p-3 text-sm">
            <span className="text-muted-foreground">Test files:</span>{" "}
            {result.test_plan.test_paths.length}
          </div>
        </div>
        {result.test_plan.setup.configuration_files.length > 0 && (
          <div className="mt-3">
            <h3 className="font-heading text-[10px] font-bold uppercase text-muted-foreground">Configuration Evidence</h3>
            <ul className="mt-2 flex flex-wrap gap-2">
              {result.test_plan.setup.configuration_files.map((path) => (
                <li key={path} className="path-text border border-dashed border-outline-variant px-2 py-1 text-xs">{path}</li>
              ))}
            </ul>
          </div>
        )}
        {result.test_plan.steps.length > 0 && (
          <ol className="mt-4 space-y-2">
            {result.test_plan.steps.map((step, index) => (
              <li key={`${index}:${step.action}`} className="border border-dashed border-outline-variant bg-surface-lowest p-3 text-sm">
                <p className="font-heading text-xs font-bold text-primary">{index + 1}. {step.action}</p>
                <p className="mt-1 text-muted-foreground">{step.description}</p>
                {step.command && <code className="path-text mt-2 block text-xs text-foreground">{step.command}</code>}
              </li>
            ))}
          </ol>
        )}
        {result.test_plan.is_truncated && (
          <p className="mt-3 text-xs text-primary">The bounded repository tree was incomplete, so this plan may omit paths.</p>
        )}
      </section>

      {error && (
        <p className="mt-5 border border-destructive bg-destructive/10 p-3 text-sm text-destructive" role="alert">
          {error}
        </p>
      )}

      <footer className="mt-6 border border-dashed border-outline-variant bg-surface p-4">
        <div className="flex flex-wrap gap-3">
          <Button variant="outline" disabled={isActionBusy} onClick={onRetry}>
            <RefreshCw /> Retry Investigation
          </Button>
          {result.investigation.outcome === "setup_failed" && (
            <Button variant="outline" disabled={isActionBusy} onClick={onEditRepository}>
              Change Project Folder
            </Button>
          )}
          {canProposeFix && (
            <Button disabled={isActionBusy} onClick={onProposeFix}>
              <Wrench /> Propose Source Fix
            </Button>
          )}
        </div>
        {canProposeFix && (
          <p className="mt-4 flex items-start gap-2 text-xs text-muted-foreground">
            <ShieldAlert className="mt-0.5 size-4 shrink-0 text-primary" aria-hidden="true" />
            A proposal performs another evidence-grounded pass and asks Gemini for one source-only patch. Nothing is applied automatically.
          </p>
        )}
      </footer>
    </section>
  );
}
