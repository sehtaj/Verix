import { LoaderCircle } from "lucide-react";

import type { WorkflowScreen } from "@/types/workflow";

const copy: Partial<Record<WorkflowScreen, { title: string; detail: string }>> = {
  loading_context: {
    title: "Inspecting Repository Context",
    detail: "Resolving the revision and preparing a bounded view of the Python project.",
  },
  running_existing_tests: {
    title: "Running Existing Tests",
    detail: "Executing the repository's own suite inside an isolated temporary Docker workspace.",
  },
  generating_tests: {
    title: "Generating Focused Tests",
    detail: "Building tests from the selected source and its bounded related context.",
  },
  investigating: {
    title: "Investigating Evidence",
    detail: "Tracing test output, generated-test evidence, and the selected source before drawing a conclusion.",
  },
  proposing_fix: {
    title: "Preparing a Source Proposal",
    detail: "Producing and validating a one-file patch for explicit review.",
  },
  verifying_fix: {
    title: "Verifying Approved Patch",
    detail: "Applying the approved patch only inside a disposable workspace and rerunning the suite.",
  },
};

const phases: Partial<Record<WorkflowScreen, string[]>> = {
  loading_context: ["Resolve Pinned Revision", "Inspect Bounded Tree", "Select Verified Target"],
  running_existing_tests: ["Prepare Repository", "Install Dependencies", "Run Existing Tests"],
  generating_tests: ["Generate Focused Tests", "Prepare Repository", "Install Dependencies", "Run Existing Suite", "Run Generated Suite"],
  investigating: ["Collect Bounded Context", "Generate Focused Tests", "Run Applicable Suites", "Classify Evidence"],
  proposing_fix: ["Refresh Investigation", "Draft One-File Patch", "Validate Patch Structure"],
  verifying_fix: ["Create Disposable Copy", "Apply Approved Patch", "Install Dependencies", "Run Patched Suite"],
};

function ActivityPhases({ screen }: { screen: WorkflowScreen }) {
  return (
    <div className="mt-6 w-full max-w-3xl">
      <p className="mb-2 text-left font-heading text-[10px] uppercase tracking-[0.1em] text-muted-foreground">
        Expected Request Work
      </p>
      <ol className="grid gap-px border border-outline-variant bg-outline-variant sm:grid-cols-2 lg:grid-cols-3">
        {(phases[screen] ?? []).map((phase) => (
          <li key={phase} className="flex items-center gap-3 bg-surface-low p-3 text-left font-heading text-xs">
            <span className="text-muted-foreground" aria-hidden="true">○</span>
            <span>{phase}</span>
          </li>
        ))}
      </ol>
    </div>
  );
}

export function WorkflowActivityBanner({ screen }: { screen: WorkflowScreen }) {
  const content = copy[screen] ?? copy.loading_context!;

  return (
    <section className="mb-6 border border-primary bg-primary/5 p-4">
      <div className="flex items-start gap-3">
        <LoaderCircle className="mt-0.5 size-5 shrink-0 animate-spin text-primary" aria-hidden="true" />
        <div>
          <p className="font-heading text-sm font-bold text-primary">{content.title}</p>
          <p className="mt-1 text-sm text-muted-foreground">{content.detail} Existing evidence remains available below.</p>
        </div>
      </div>
      <ActivityPhases screen={screen} />
    </section>
  );
}

export function WorkflowLoadingPanel({ screen }: { screen: WorkflowScreen }) {
  const content = copy[screen] ?? copy.loading_context!;

  return (
    <section className="mx-auto flex min-h-[60vh] max-w-4xl flex-col items-center justify-center border border-dashed border-outline-variant bg-surface-low/80 p-8 text-center">
      <LoaderCircle className="size-10 animate-spin text-primary" aria-hidden="true" />
      <p className="mt-5 font-heading text-xs uppercase tracking-[0.18em] text-primary">Working</p>
      <h1 className="mt-2 font-heading text-2xl font-bold md:text-3xl">{content.title}</h1>
      <p className="mt-3 max-w-xl text-muted-foreground">{content.detail}</p>
      <p className="mt-8 border border-dashed border-outline-variant px-4 py-2 font-heading text-xs text-muted-foreground">
        Keep this tab open while the request completes.
      </p>
      <ActivityPhases screen={screen} />
    </section>
  );
}
