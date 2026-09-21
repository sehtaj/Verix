"use client";

import { AlertTriangle, CheckCircle2, Search, ShieldAlert, WandSparkles, XCircle } from "lucide-react";

import { Button } from "@/components/ui/button";
import { ExecutionEvidence, PreparationEvidence } from "@/components/verix/execution-evidence";
import { didInstallationSucceed, getExecutionStatus } from "@/lib/repository-results";
import type { RepositoryTestRun } from "@/types/api";

type TestResultPanelProps = {
  result: RepositoryTestRun;
  error: string | null;
  isActionBusy?: boolean;
  canUseTarget: boolean;
  onRetry: () => void;
  onGenerate: () => void;
  onInvestigate: () => void;
  onEditRepository: () => void;
};

function FailureMasterDetail({ result }: { result: RepositoryTestRun }) {
  const outputLines = result.execution.output.split("\n").filter((line) => line.trim());
  const failureSummary =
    outputLines.find((line) => /\b(?:FAILED|ERROR|AssertionError)\b/i.test(line)) ??
    outputLines[0] ??
    "The existing suite returned a non-zero exit code.";

  return (
    <section className="mt-5" aria-label="Existing-test failure evidence">
      <div className="flex flex-wrap items-center gap-x-5 gap-y-2 border border-outline-variant bg-surface p-3 font-heading text-xs">
        <span>Existing Tests</span>
        <span className="text-muted-foreground">Runner: {result.test_runner}</span>
        <span className="text-destructive">Status: Failed</span>
        <span className="tabular-nums text-muted-foreground">Exit: {result.execution.return_code}</span>
      </div>

      <div className="mt-4 flex gap-6 border-b border-outline-variant font-heading text-xs">
        <span className="border-b-2 border-primary pb-3 text-primary">Existing Tests</span>
        <span className="pb-3 text-muted-foreground">Generated Tests (Not Run)</span>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-[220px_minmax(0,1fr)]">
        <aside className="border border-destructive bg-destructive/5 p-3">
          <p className="font-heading text-[10px] uppercase text-muted-foreground">Log Summary</p>
          <p className="mt-2 break-words font-heading text-xs text-destructive">{failureSummary}</p>
          <p className="mt-4 text-xs text-muted-foreground">Full bounded output is preserved in the detail panel.</p>
        </aside>

        <article className="min-w-0 border border-outline-variant bg-surface">
          <header className="flex items-start gap-3 border-b border-dashed border-outline-variant bg-surface-high p-4">
            <XCircle className="mt-0.5 size-5 shrink-0 text-destructive" aria-hidden="true" />
            <div className="min-w-0">
              <p className="font-heading text-xs text-muted-foreground">Existing Suite Failure</p>
              <p className="mt-1 break-words font-heading text-sm text-destructive">{failureSummary}</p>
            </div>
          </header>
          <dl className="grid gap-px bg-outline-variant sm:grid-cols-2">
            <div className="bg-surface-low p-3">
              <dt className="font-heading text-[10px] uppercase text-muted-foreground">Test Runner</dt>
              <dd className="mt-1 font-heading text-sm uppercase">{result.test_runner}</dd>
            </div>
            <div className="bg-surface-low p-3">
              <dt className="font-heading text-[10px] uppercase text-muted-foreground">Execution Result</dt>
              <dd className="mt-1 font-heading text-sm text-destructive">Non-zero exit {result.execution.return_code}</dd>
            </div>
          </dl>
          <div className="p-4">
            <ExecutionEvidence title="Full Bounded Failure Logs" execution={result.execution} defaultExpanded />
          </div>
        </article>
      </div>
    </section>
  );
}

export function TestResultPanel({ result, error, isActionBusy = false, canUseTarget, onRetry, onGenerate, onInvestigate, onEditRepository }: TestResultPanelProps) {
  const executionStatus = getExecutionStatus(result.execution);
  const setupFailed = !didInstallationSucceed(result.installation);
  const failed = !setupFailed && executionStatus === "failed";
  const passed = !setupFailed && executionStatus === "passed";
  const noTests = !setupFailed && executionStatus === "no_tests";
  const timedOut = !setupFailed && executionStatus === "timed_out";

  const heading = setupFailed
    ? "Repository Setup Did Not Complete"
    : failed
      ? "Test Run Found a Failure"
      : passed
        ? "Existing Test Suite Passed"
        : noTests
          ? "No Tests Were Collected"
          : timedOut
            ? "Existing Test Run Timed Out"
            : "Existing Tests Did Not Run";
  const Icon = passed ? CheckCircle2 : failed ? XCircle : AlertTriangle;
  const statusClass = passed ? "text-success" : failed || timedOut ? "text-destructive" : "text-primary";

  return (
    <section className="mx-auto w-full max-w-5xl">
      <header>
        <div className={`flex items-center gap-3 ${statusClass}`}>
          <Icon className="size-8" aria-hidden="true" />
          <h1 className="font-heading text-3xl font-bold">{heading}</h1>
        </div>
        <p className="mt-2 text-muted-foreground">
          Verix preserved repository preparation, dependency setup, and test evidence separately.
        </p>
      </header>

      <div className="mt-6 space-y-4">
        <PreparationEvidence preparation={result.preparation} />
        <ExecutionEvidence title="Dependency Installation" execution={result.installation} defaultExpanded={setupFailed} />
        {failed ? (
          <FailureMasterDetail result={result} />
        ) : (
          <ExecutionEvidence title={`Existing Tests · ${result.test_runner}`} execution={result.execution} defaultExpanded={!passed} />
        )}
      </div>

      {error && (
        <p className="mt-5 border border-destructive bg-destructive/10 p-3 text-sm text-destructive" role="alert">
          {error}
        </p>
      )}

      <div className="mt-6 border border-dashed border-outline-variant bg-surface p-4">
        <div className="flex flex-wrap gap-3">
          <Button variant="outline" disabled={isActionBusy} onClick={onRetry}>Retry Existing Tests</Button>
          <Button variant="outline" disabled={isActionBusy || !canUseTarget} onClick={onGenerate}><WandSparkles /> Generate Focused Tests</Button>
          {!passed && (
            <Button disabled={isActionBusy || !canUseTarget} onClick={onInvestigate}><Search /> Investigate Evidence</Button>
          )}
          {setupFailed && (
            <Button variant="outline" disabled={isActionBusy} onClick={onEditRepository}>
              Change Project Folder
            </Button>
          )}
        </div>
        {!canUseTarget && (
          <p className="mt-4 text-xs text-destructive">
            Select a verified Python source target before generating or investigating focused evidence.
          </p>
        )}
        {!passed && (
          <p className="mt-4 flex items-start gap-2 text-xs text-muted-foreground">
            <ShieldAlert className="mt-0.5 size-4 shrink-0 text-primary" aria-hidden="true" />
            Investigation performs a fresh generated-and-existing test pass for the pinned target. It does not merely reinterpret this log.
          </p>
        )}
      </div>
    </section>
  );
}
