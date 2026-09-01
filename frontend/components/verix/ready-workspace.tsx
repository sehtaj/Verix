"use client";

import { useState } from "react";
import { Archive, Braces, Eye, FlaskConical, Info, ListTree, ShieldCheck, Sparkles, Target, WandSparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import { ExecutionEvidence, PreparationEvidence } from "@/components/verix/execution-evidence";
import type { RepositoryContext, RepositoryTestRun } from "@/types/api";

type ReadyWorkspaceProps = {
  context: RepositoryContext;
  selectedTargetPath: string;
  mode: "existing" | "generate";
  error: string | null;
  onRunExisting: () => void;
  onGenerate: () => void;
  onPreview: () => void;
  onSelectTarget: (path: string) => void;
  priorTestRun?: RepositoryTestRun | null;
};

function TargetContext({ context, selectedTargetPath }: Pick<ReadyWorkspaceProps, "context" | "selectedTargetPath">) {
  const relatedTests = context.generation_selection.related_test_paths;

  return (
    <section className="border border-outline bg-surface">
      <div className="flex items-center justify-between border-b border-dashed border-outline-variant bg-surface-high px-4 py-2">
        <h2 className="font-heading text-xs uppercase text-muted-foreground">Target Context</h2>
        <span className="border border-dashed border-outline-variant px-2 py-1 font-heading text-xs">Lang: Python</span>
      </div>
      <div className="space-y-4 p-5">
        <div className="flex items-start gap-3">
          <Braces className="mt-0.5 size-5 shrink-0 text-primary" aria-hidden="true" />
          <div className="min-w-0">
            <p className="path-text font-heading text-sm text-primary">{selectedTargetPath}</p>
            <p className="mt-2 border-l-2 border-primary pl-3 text-muted-foreground">
              Verified Python source selected from the bounded repository context.
            </p>
          </div>
        </div>
        <div className="border-t border-dashed border-outline-variant pt-4">
          <h3 className="font-heading text-xs uppercase text-muted-foreground">Related Test Context</h3>
          {relatedTests.length > 0 ? (
            <ul className="mt-2 space-y-2">
              {relatedTests.map((path) => (
                <li key={path} className="path-text border border-dashed border-outline-variant bg-surface-lowest px-3 py-2 font-heading text-xs">
                  {path}
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-2 text-sm text-muted-foreground">No related existing test files were selected.</p>
          )}
        </div>
      </div>
    </section>
  );
}

export function ReadyWorkspace({
  context,
  selectedTargetPath,
  mode,
  error,
  onRunExisting,
  onGenerate,
  onPreview,
  onSelectTarget,
  priorTestRun = null,
}: ReadyWorkspaceProps) {
  const [targetPickerOpen, setTargetPickerOpen] = useState(false);
  const hasTarget = selectedTargetPath.length > 0;
  const isExisting = mode === "existing";

  return (
    <section className="mx-auto w-full max-w-5xl">
      <header className="mb-7">
        <div className="flex items-center gap-3">
          {isExisting ? <Target className="size-8 text-primary" aria-hidden="true" /> : <FlaskConical className="size-8 text-primary" aria-hidden="true" />}
          <h1 className="font-heading text-3xl font-bold text-primary">
            {isExisting ? "Ready to Verify" : "No Existing Tests Found"}
          </h1>
        </div>
        <p className="mt-2 text-lg text-muted-foreground">
          {isExisting
            ? "Verix selected the target file and related test context."
            : "Verix can generate focused tests for the selected source to establish a baseline."}
        </p>
      </header>

      {!hasTarget && (
        <div className="mb-5 border border-destructive bg-destructive/5 p-4 text-destructive" role="alert">
          No usable Python source target was found. Choose another repository or project folder.
        </div>
      )}

      <TargetContext context={context} selectedTargetPath={selectedTargetPath || "No target selected"} />

      {!isExisting && hasTarget && (
        <section className="mt-5 grid gap-px border border-outline-variant bg-outline-variant md:grid-cols-2">
          <div className="bg-surface p-4">
            <h2 className="flex items-center gap-2 font-heading text-xs font-bold uppercase text-primary">
              <Target className="size-4" aria-hidden="true" /> Generation Scope
            </h2>
            <ul className="mt-3 space-y-2 text-sm text-muted-foreground">
              <li>[+] Normal behaviour paths</li>
              <li>[+] Edge cases and boundary conditions</li>
              <li>[+] Error handling and exceptions</li>
              <li>[+] Relevant mocks and fixtures</li>
            </ul>
          </div>
          <div className="bg-surface p-4">
            <h2 className="flex items-center gap-2 font-heading text-xs font-bold uppercase text-primary">
              <ShieldCheck className="size-4" aria-hidden="true" /> Execution Boundary
            </h2>
            <p className="mt-3 text-sm text-muted-foreground">
              Generated tests execute only in an isolated temporary Docker workspace. Repository code is not run on the host.
            </p>
          </div>
        </section>
      )}

      {error && <p className="mt-5 border border-destructive bg-destructive/10 p-3 text-sm text-destructive" role="alert">{error}</p>}

      <section className="mt-5 border border-primary/70 bg-surface-low p-4">
        <div className="flex flex-col gap-3 md:flex-row md:items-center">
          {isExisting && (
            <Button size="lg" onClick={onRunExisting}>
              <span aria-hidden="true">▷</span> Run Existing Tests
            </Button>
          )}
          <Button size="lg" variant={isExisting ? "outline" : "default"} disabled={!hasTarget} onClick={onGenerate}>
            <WandSparkles /> Generate Focused Tests
          </Button>
          <Button size="lg" variant="outline" disabled={!hasTarget} onClick={onPreview}>
            <Eye /> Preview Context
          </Button>
          {!isExisting && (
            <Button size="lg" variant="outline" onClick={() => setTargetPickerOpen((open) => !open)}>
              <ListTree /> Choose Another Target
            </Button>
          )}
        </div>
        {!isExisting && targetPickerOpen && (
          <div className="mt-4 border-t border-dashed border-outline-variant pt-4">
            <label htmlFor="target-selector" className="mb-2 block font-heading text-xs font-bold uppercase text-muted-foreground">
              Verified Python Source Target
            </label>
            <select
              id="target-selector"
              name="target-selector"
              autoComplete="off"
              className="h-11 w-full border border-outline-variant bg-surface-lowest px-3 font-heading text-sm text-foreground focus-visible:border-primary focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary"
              value={selectedTargetPath}
              onChange={(event) => onSelectTarget(event.target.value)}
            >
              {context.test_plan.source_paths.map((path) => (
                <option key={path} value={path}>{path}</option>
              ))}
            </select>
            <p className="mt-2 text-xs text-muted-foreground">
              Selecting a target asks the backend to verify it against the pinned revision before replacing this context.
            </p>
          </div>
        )}
        <p className="mt-4 flex items-center gap-2 text-xs text-muted-foreground">
          <Info className="size-4" aria-hidden="true" /> Requests use the pinned revision {context.revision.slice(0, 12)}.
        </p>
      </section>

      <section className="mt-8 flex min-h-64 flex-col items-center justify-center border border-dashed border-outline-variant bg-surface-lowest p-8 text-center">
        {isExisting ? <Archive className="size-10 text-outline" aria-hidden="true" /> : <Sparkles className="size-10 text-outline" aria-hidden="true" />}
        <h2 className="mt-4 font-heading text-xl font-bold">
          {isExisting ? "No Evidence Yet" : "No Generated Tests Yet"}
        </h2>
        <p className="mt-2 max-w-md text-muted-foreground">
          {isExisting
            ? "Run the existing suite to collect baseline evidence and begin verification."
            : "Generate focused tests to review their behaviour and execution evidence."}
        </p>
      </section>

      {!isExisting && priorTestRun && (
        <section className="mt-5 space-y-4" aria-label="Previous existing-test evidence">
          <h2 className="font-heading text-xs font-bold uppercase text-muted-foreground">
            Previous Existing-Test Evidence
          </h2>
          <PreparationEvidence preparation={priorTestRun.preparation} />
          <ExecutionEvidence title="Dependency Installation" execution={priorTestRun.installation} />
          <ExecutionEvidence title={`Existing Tests · ${priorTestRun.test_runner}`} execution={priorTestRun.execution} defaultExpanded />
        </section>
      )}
    </section>
  );
}
