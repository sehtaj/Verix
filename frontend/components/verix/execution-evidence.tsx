"use client";

import { useState } from "react";
import { AlertTriangle, Check, CheckCircle2, ChevronDown, Clock3, Copy, MinusCircle, TerminalSquare, XCircle } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { getExecutionLabel, getExecutionStatus } from "@/lib/repository-results";
import type { RepositoryExecution, RepositoryPreparation } from "@/types/api";

const numberFormatter = new Intl.NumberFormat();

function useCopyText() {
  const [copyStatus, setCopyStatus] = useState<"idle" | "copied" | "failed">("idle");

  async function copy(text: string) {
    try {
      await navigator.clipboard.writeText(text);
      setCopyStatus("copied");
    } catch {
      setCopyStatus("failed");
    }
  }

  return { copy, copyStatus };
}

const statusPresentation = {
  passed: { Icon: CheckCircle2, className: "border-success text-success bg-success/5" },
  failed: { Icon: XCircle, className: "border-destructive text-destructive bg-destructive/5" },
  timed_out: { Icon: Clock3, className: "border-destructive text-destructive bg-destructive/5" },
  skipped: { Icon: MinusCircle, className: "border-outline text-muted-foreground bg-surface-low" },
  no_tests: { Icon: AlertTriangle, className: "border-primary text-primary bg-primary/5" },
};

type ExecutionEvidenceProps = {
  title: string;
  execution: RepositoryExecution;
  defaultExpanded?: boolean;
};

export function ExecutionEvidence({ title, execution, defaultExpanded = false }: ExecutionEvidenceProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const status = getExecutionStatus(execution);
  const presentation = statusPresentation[status];
  const Icon = presentation.Icon;
  const { copy, copyStatus } = useCopyText();

  return (
    <section className={cn("border", presentation.className)}>
      <div className="flex items-center gap-2 p-2 pr-3">
        <button
          type="button"
          className="flex min-w-0 flex-1 items-center justify-between gap-4 p-2 text-left hover:bg-white/5"
          aria-expanded={expanded}
          onClick={() => setExpanded((value) => !value)}
        >
          <span className="flex min-w-0 items-center gap-3">
            <Icon className="size-5 shrink-0" aria-hidden="true" />
            <span>
              <span className="block font-heading text-xs uppercase tracking-[0.1em] text-foreground">{title}</span>
              <span className="mt-1 block font-heading text-sm font-bold">{getExecutionLabel(status)}</span>
            </span>
          </span>
          <span className="flex shrink-0 items-center gap-3 font-heading text-xs">
            {execution.return_code !== null && <span>Exit {execution.return_code}</span>}
            <ChevronDown className={cn("size-4 transition-transform", expanded && "rotate-180")} aria-hidden="true" />
          </span>
        </button>
        <Button
          size="icon-sm"
          variant="ghost"
          aria-label={`Copy ${title} output`}
          title={`Copy ${title} output`}
          onClick={() => copy(execution.output)}
        >
          {copyStatus === "copied" ? <Check aria-hidden="true" /> : copyStatus === "failed" ? <AlertTriangle className="text-destructive" aria-hidden="true" /> : <Copy aria-hidden="true" />}
        </Button>
        {copyStatus === "failed" && <span className="text-xs text-destructive">Copy failed</span>}
        <span className="sr-only" aria-live="polite">
          {copyStatus === "copied" ? `${title} output copied.` : copyStatus === "failed" ? `Could not copy ${title} output.` : ""}
        </span>
      </div>
      {expanded && (
        <pre className="max-h-80 overflow-auto whitespace-pre-wrap border-t border-current/30 bg-surface-lowest p-4 font-heading text-xs leading-5 text-foreground">
          <code>{execution.output || "No output was returned."}</code>
        </pre>
      )}
    </section>
  );
}

export function PreparationEvidence({ preparation }: { preparation: RepositoryPreparation }) {
  return (
    <dl className="grid gap-px border border-outline-variant bg-outline-variant sm:grid-cols-3">
      <div className="bg-surface-low p-3">
        <dt className="font-heading text-[10px] uppercase text-muted-foreground">Prepared Files</dt>
        <dd className="mt-1 font-heading text-sm tabular-nums">{numberFormatter.format(preparation.file_count)}</dd>
      </div>
      <div className="bg-surface-low p-3">
        <dt className="font-heading text-[10px] uppercase text-muted-foreground">Workspace Bytes</dt>
        <dd className="mt-1 font-heading text-sm tabular-nums">{numberFormatter.format(preparation.total_bytes)}</dd>
      </div>
      <div className="bg-surface-low p-3">
        <dt className="font-heading text-[10px] uppercase text-muted-foreground">Skipped Entries</dt>
        <dd className="mt-1 font-heading text-sm tabular-nums">{numberFormatter.format(preparation.skipped_entries)}</dd>
      </div>
    </dl>
  );
}

export function CodeEvidence({ title, code }: { title: string; code: string }) {
  const [expanded, setExpanded] = useState(true);
  const { copy, copyStatus } = useCopyText();

  return (
    <section className="border border-dashed border-outline-variant bg-surface-lowest">
      <header className="flex flex-col gap-3 border-b border-dashed border-outline-variant px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
        <h3 className="flex items-center gap-2 font-heading text-xs uppercase text-primary">
          <TerminalSquare className="size-4" aria-hidden="true" /> {title}
        </h3>
        <div className="flex items-center gap-2">
          <Button size="sm" variant="ghost" onClick={() => copy(code)}>
            {copyStatus === "copied" ? <Check aria-hidden="true" /> : copyStatus === "failed" ? <AlertTriangle className="text-destructive" aria-hidden="true" /> : <Copy aria-hidden="true" />}
            {copyStatus === "copied" ? "Copied" : copyStatus === "failed" ? "Copy Failed" : "Copy Code"}
          </Button>
          <Button size="sm" variant="ghost" onClick={() => setExpanded((value) => !value)}>
            {expanded ? "Collapse" : "Expand"}
          </Button>
        </div>
      </header>
      <span className="sr-only" aria-live="polite">
        {copyStatus === "copied" ? `${title} copied.` : copyStatus === "failed" ? `Could not copy ${title}.` : ""}
      </span>
      {expanded && (
        <pre className="max-h-[28rem] overflow-auto whitespace-pre p-4 font-heading text-xs leading-5">
          <code>{code}</code>
        </pre>
      )}
    </section>
  );
}
