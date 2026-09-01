"use client";

import {
  AlertTriangle,
  CheckCircle2,
  RefreshCw,
  ShieldCheck,
  XCircle,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { ExecutionEvidence } from "@/components/verix/execution-evidence";
import { didInstallationSucceed, getExecutionStatus } from "@/lib/repository-results";
import type { RepositoryFixVerificationRun } from "@/types/api";

type VerificationResultPanelProps = {
  result: RepositoryFixVerificationRun;
  error: string | null;
  isActionBusy?: boolean;
  onRetry: () => void;
};

export function VerificationResultPanel({ result, error, isActionBusy = false, onRetry }: VerificationResultPanelProps) {
  const installationStatus = getExecutionStatus(result.installation);
  const executionStatus = getExecutionStatus(result.execution);
  const installationSucceeded = didInstallationSucceed(result.installation);
  const safetyConfirmed = result.applied_in_disposable_workspace && !result.github_changed;
  const passed = safetyConfirmed && installationSucceeded && executionStatus === "passed";
  const failed = !safetyConfirmed || !installationSucceeded || executionStatus === "failed";
  const ResultIcon = passed ? CheckCircle2 : failed ? XCircle : AlertTriangle;
  const resultColor = passed ? "text-success" : failed ? "text-destructive" : "text-primary";

  return (
    <section className="mx-auto w-full max-w-5xl">
      <header>
        <div className={`flex items-center gap-3 ${resultColor}`}>
          <ResultIcon className="size-9" aria-hidden="true" />
          <h1 className="text-balance font-heading text-3xl font-bold">
            {passed
              ? "Patched Suite Passed in the Temporary Workspace"
              : "Patch Verification Needs Review"}
          </h1>
        </div>
        <p className="mt-3 max-w-3xl text-muted-foreground">
          {passed
            ? "The approved patch produced passing test evidence in the disposable environment. This is evidence for human review, not proof that the change is correct."
            : "The approved patch was tested, but the returned evidence does not establish a passing result."}
        </p>
      </header>

      <section className="mt-6 grid gap-4 sm:grid-cols-2">
        <div className={result.applied_in_disposable_workspace ? "border border-success/70 bg-success/5 p-4" : "border border-destructive bg-destructive/5 p-4"}>
          <p className="flex items-start gap-3">
            {result.applied_in_disposable_workspace ? <ShieldCheck className="mt-0.5 size-5 shrink-0 text-success" aria-hidden="true" /> : <XCircle className="mt-0.5 size-5 shrink-0 text-destructive" aria-hidden="true" />}
            <span>
              <strong className={`block font-heading text-xs uppercase ${result.applied_in_disposable_workspace ? "text-success" : "text-destructive"}`}>Disposable Application</strong>
              <span className="mt-1 block text-sm">{result.applied_in_disposable_workspace ? "Applied only in a temporary workspace" : "Disposable application not confirmed"}</span>
            </span>
          </p>
        </div>
        <div className={!result.github_changed ? "border border-success/70 bg-success/5 p-4" : "border border-destructive bg-destructive/5 p-4"}>
          <p className="flex items-start gap-3">
            {!result.github_changed ? <ShieldCheck className="mt-0.5 size-5 shrink-0 text-success" aria-hidden="true" /> : <XCircle className="mt-0.5 size-5 shrink-0 text-destructive" aria-hidden="true" />}
            <span>
              <strong className={`block font-heading text-xs uppercase ${!result.github_changed ? "text-success" : "text-destructive"}`}>GitHub Safety</strong>
              <span className="mt-1 block text-sm">{result.github_changed ? "GitHub change reported" : "GitHub remained unchanged"}</span>
            </span>
          </p>
        </div>
      </section>

      <dl className="mt-5 grid gap-px border border-outline-variant bg-outline-variant sm:grid-cols-3">
        <div className="min-w-0 bg-surface-low p-3 sm:col-span-2">
          <dt className="font-heading text-[10px] uppercase text-muted-foreground">Verified Target</dt>
          <dd className="path-text mt-1 font-heading text-sm text-primary">{result.target_path}</dd>
        </div>
        <div className="bg-surface-low p-3">
          <dt className="font-heading text-[10px] uppercase text-muted-foreground">Runner</dt>
          <dd className="mt-1 font-heading text-sm uppercase">{result.test_runner}</dd>
        </div>
      </dl>

      <div className="mt-5 space-y-4">
        <ExecutionEvidence
          title="Dependency Installation"
          execution={result.installation}
          defaultExpanded={installationStatus !== "passed"}
        />
        <ExecutionEvidence
          title="Patched Test Suite"
          execution={result.execution}
          defaultExpanded={!passed}
        />
      </div>

      {error && (
        <p className="mt-5 border border-destructive bg-destructive/10 p-3 text-sm text-destructive" role="alert">
          {error}
        </p>
      )}

      <footer className="mt-6 flex flex-wrap gap-3 border border-dashed border-outline-variant bg-surface p-4">
        <Button variant="outline" disabled={isActionBusy} onClick={onRetry}>
          <RefreshCw /> Retry Disposable Verification
        </Button>
      </footer>
    </section>
  );
}
