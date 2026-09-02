"use client";

import { useState } from "react";
import { Dialog } from "@base-ui/react/dialog";
import {
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  FileDiff,
  ShieldCheck,
  X,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { RepositoryFixProposalRun } from "@/types/api";

type FixReviewPanelProps = {
  result: RepositoryFixProposalRun;
  error: string | null;
  isActionBusy?: boolean;
  onBack: () => void;
  onApproveAndVerify: () => void;
};

function DiffView({ patch }: { patch: string }) {
  return (
    <pre
      tabIndex={0}
      aria-label="Proposed unified diff"
      className="max-h-[34rem] overflow-auto border border-outline-variant bg-surface-lowest p-0 font-heading text-xs leading-5"
    >
      <code className="block min-w-max">
        {patch.split("\n").map((line, index) => {
          const addition = line.startsWith("+") && !line.startsWith("+++");
          const removal = line.startsWith("-") && !line.startsWith("---");
          const header = line.startsWith("@@") || line.startsWith("+++") || line.startsWith("---");
          return (
            <span
              key={`${index}:${line}`}
              className={cn(
                "content-auto block min-h-5 whitespace-pre px-4",
                addition && "bg-success/10 text-success",
                removal && "bg-destructive/10 text-destructive",
                header && "bg-primary/10 text-primary",
              )}
            >
              {line || " "}
            </span>
          );
        })}
      </code>
    </pre>
  );
}

export function FixReviewPanel({
  result,
  error,
  isActionBusy = false,
  onBack,
  onApproveAndVerify,
}: FixReviewPanelProps) {
  const [reviewConfirmed, setReviewConfirmed] = useState(false);
  const [confirmationOpen, setConfirmationOpen] = useState(false);
  const { proposal } = result;

  return (
    <section className="mx-auto w-full max-w-5xl">
      <header>
        <div className="flex items-center gap-3 text-primary">
          <FileDiff className="size-8" aria-hidden="true" />
          <h1 className="text-balance font-heading text-3xl font-bold">Review Source Proposal</h1>
        </div>
        <p className="mt-2 text-muted-foreground">
          Review every changed line before approving a disposable verification run.
        </p>
      </header>

      <section className="mt-6 border border-primary bg-surface">
        <div className="border-b border-dashed border-outline-variant bg-surface-high p-4">
          <p className="font-heading text-xs uppercase tracking-[0.12em] text-muted-foreground">Proposal Summary</p>
          <h2 className="mt-2 break-words text-lg font-bold text-foreground">{proposal.summary}</h2>
        </div>
        <dl className="grid gap-px bg-outline-variant sm:grid-cols-2">
          <div className="min-w-0 bg-surface-low p-3">
            <dt className="font-heading text-[10px] uppercase text-muted-foreground">Pinned Revision</dt>
            <dd className="path-text mt-1 font-heading text-xs">{proposal.revision}</dd>
          </div>
          <div className="min-w-0 bg-surface-low p-3">
            <dt className="font-heading text-[10px] uppercase text-muted-foreground">Only Target File</dt>
            <dd className="path-text mt-1 font-heading text-xs text-primary">{proposal.target_path}</dd>
          </div>
        </dl>
      </section>

      <section className="mt-5">
        <h2 className="mb-3 font-heading text-xs font-bold uppercase text-muted-foreground">Unified Diff</h2>
        <DiffView patch={proposal.patch} />
      </section>

      <section className="mt-5 grid gap-3 sm:grid-cols-3">
        <div className={cn("border p-3", proposal.validated ? "border-success bg-success/5" : "border-destructive bg-destructive/5")}>
          <p className="font-heading text-[10px] uppercase text-muted-foreground">Validation</p>
          <p className="mt-1 flex items-center gap-2 text-sm">
            {proposal.validated ? <CheckCircle2 className="size-4 text-success" aria-hidden="true" /> : <AlertTriangle className="size-4 text-destructive" aria-hidden="true" />}
            {proposal.validated ? "Patch structure validated" : "Patch validation failed"}
          </p>
        </div>
        <div className="border border-primary/60 bg-primary/5 p-3">
          <p className="font-heading text-[10px] uppercase text-muted-foreground">Approval</p>
          <p className="mt-1 text-sm">{proposal.approval_required ? "Explicit approval required" : "Approval not requested"}</p>
        </div>
        <div className="border border-outline-variant bg-surface-low p-3">
          <p className="font-heading text-[10px] uppercase text-muted-foreground">Applied</p>
          <p className="mt-1 text-sm">{proposal.applied ? "Already applied" : "Not applied anywhere"}</p>
        </div>
      </section>

      <div className="mt-5 border border-success/70 bg-success/5 p-4 text-sm">
        <p className="flex items-start gap-2">
          <ShieldCheck className="mt-0.5 size-5 shrink-0 text-success" aria-hidden="true" />
          <span>
            <strong>GitHub and your local checkout are unchanged.</strong> Approval applies this one-file patch only inside a new disposable Docker workspace.
          </span>
        </p>
      </div>

      {error && (
        <p className="mt-5 border border-destructive bg-destructive/10 p-3 text-sm text-destructive" role="alert">
          {error}
        </p>
      )}

      <label className="mt-6 flex cursor-pointer items-start gap-3 border border-dashed border-outline p-4 hover:border-primary">
        <input
          type="checkbox"
          className="mt-0.5 size-5 accent-[var(--primary)]"
          checked={reviewConfirmed}
          onChange={(event) => setReviewConfirmed(event.target.checked)}
        />
        <span className="text-sm">
          I reviewed the complete diff and understand that approval only verifies it in a temporary workspace.
        </span>
      </label>

      <footer className="mt-4 flex flex-col-reverse gap-3 sm:flex-row sm:justify-between">
        <Button variant="outline" disabled={isActionBusy} onClick={onBack}>
          <ArrowLeft /> Back to Investigation
        </Button>
        <Button
          disabled={isActionBusy || !reviewConfirmed || !proposal.validated || !proposal.approval_required || proposal.applied}
          onClick={() => setConfirmationOpen(true)}
        >
          <ShieldCheck /> Approve & Verify Temporarily
        </Button>
      </footer>

      <Dialog.Root open={confirmationOpen} onOpenChange={setConfirmationOpen}>
        <Dialog.Portal>
          <Dialog.Backdrop className="fixed inset-0 z-[80] bg-black/80" />
          <Dialog.Viewport className="dialog-safe fixed inset-0 z-[81] grid place-items-center overflow-y-auto overscroll-contain p-4">
            <Dialog.Popup className="w-full max-w-xl border border-primary bg-surface outline-none focus-visible:ring-2 focus-visible:ring-primary">
              <header className="flex items-start justify-between gap-4 border-b border-dashed border-outline-variant p-5">
                <div>
                  <Dialog.Title className="font-heading text-xl font-bold text-primary">Confirm Disposable Verification</Dialog.Title>
                  <Dialog.Description className="mt-2 text-sm text-muted-foreground">
                    Verix will test the exact reviewed patch against the pinned revision.
                  </Dialog.Description>
                </div>
                <Dialog.Close aria-label="Cancel verification" className="grid size-9 shrink-0 place-items-center border border-outline hover:border-primary hover:text-primary">
                  <X className="size-4" aria-hidden="true" />
                </Dialog.Close>
              </header>
              <ul className="space-y-3 p-5 text-sm">
                <li className="border border-dashed border-outline-variant p-3"><strong>Revision:</strong> <span className="path-text">{proposal.revision}</span></li>
                <li className="border border-dashed border-outline-variant p-3"><strong>Changed file:</strong> <span className="path-text text-primary">{proposal.target_path}</span></li>
                <li className="border border-dashed border-outline-variant p-3">The patch is applied only inside a disposable workspace.</li>
                <li className="border border-dashed border-outline-variant p-3">No GitHub or local-checkout write is performed.</li>
              </ul>
              <footer className="flex flex-col-reverse gap-3 border-t border-dashed border-outline-variant p-5 sm:flex-row sm:justify-end">
                <Dialog.Close render={<Button variant="outline" />}>Cancel</Dialog.Close>
                <Button
                  onClick={() => {
                    setConfirmationOpen(false);
                    onApproveAndVerify();
                  }}
                >
                  Approve & Run Verification
                </Button>
              </footer>
            </Dialog.Popup>
          </Dialog.Viewport>
        </Dialog.Portal>
      </Dialog.Root>
    </section>
  );
}
