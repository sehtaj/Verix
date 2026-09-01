"use client";

import { useState, type ReactNode } from "react";
import { Dialog } from "@base-ui/react/dialog";
import { Menu, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import type { WorkflowStepEvidence } from "@/lib/repository-results";
import type { RepositoryContext } from "@/types/api";
import type { WorkflowScreen } from "@/types/workflow";
import { AppHeader } from "./app-header";
import { RepositorySidebar } from "./repository-sidebar";
import { WorkflowStepper } from "./workflow-stepper";

type AppShellProps = {
  screen: WorkflowScreen;
  stepEvidence: WorkflowStepEvidence;
  context: RepositoryContext | null;
  selectedTargetPath: string;
  isBusy: boolean;
  isPreviewLoading: boolean;
  previewError: string | null;
  onNewVerification: () => void;
  onSelectTarget: (path: string) => void;
  onPreviewContext: () => void;
  children: ReactNode;
};

export function AppShell({
  screen,
  stepEvidence,
  context,
  selectedTargetPath,
  isBusy,
  isPreviewLoading,
  previewError,
  onNewVerification,
  onSelectTarget,
  onPreviewContext,
  children,
}: AppShellProps) {
  const [mobileContextOpen, setMobileContextOpen] = useState(false);

  const sidebarProps = {
    context,
    selectedTargetPath,
    isBusy,
    isPreviewLoading,
    isPreviewDisabled: screen === "loading_context" || isPreviewLoading,
    previewError,
    onSelectTarget,
    onPreviewContext,
  };

  return (
    <div className="min-h-screen bg-background text-foreground">
      <a
        href="#main-content"
        className="fixed left-3 top-3 z-[100] -translate-y-20 border border-primary bg-background px-4 py-2 font-heading text-xs text-primary focus-visible:translate-y-0"
      >
        Skip to Main Content
      </a>
      <AppHeader context={context} selectedTargetPath={selectedTargetPath} onNewVerification={onNewVerification} />

      <div className="viewport-height flex overflow-hidden pt-16">
        <RepositorySidebar {...sidebarProps} id="repository-context-desktop" className="hidden w-64 shrink-0 border-r border-dashed border-outline-variant lg:flex" />

        <div className="flex min-w-0 flex-1 flex-col">
          <WorkflowStepper screen={screen} evidence={stepEvidence} />
          <div className="flex flex-col gap-2 border-b border-dashed border-outline-variant px-4 py-2 sm:flex-row sm:items-center sm:justify-between lg:hidden">
            <Dialog.Root open={mobileContextOpen} onOpenChange={setMobileContextOpen}>
              <Dialog.Trigger
                render={<Button variant="outline" size="sm" />}
              >
                <Menu /> Repository Context
              </Dialog.Trigger>
              <Dialog.Portal>
                <Dialog.Backdrop className="fixed inset-0 z-[60] bg-black/70" />
                <Dialog.Viewport className="fixed inset-0 z-[61] flex justify-start overscroll-contain">
                  <Dialog.Popup className="h-full w-[min(88vw,320px)] border-r border-primary bg-surface-low outline-none focus-visible:ring-2 focus-visible:ring-primary">
                    <Dialog.Title className="sr-only">Repository Context</Dialog.Title>
                    <Dialog.Description className="sr-only">
                      Inspect the bounded repository tree and select a source target.
                    </Dialog.Description>
                    <Dialog.Close
                      aria-label="Close repository context"
                      className="absolute right-2 top-2 z-10 flex size-9 items-center justify-center border border-outline bg-surface text-foreground hover:border-primary hover:text-primary"
                    >
                      <X className="size-4" aria-hidden="true" />
                    </Dialog.Close>
                    <RepositorySidebar
                      {...sidebarProps}
                      id="repository-context-mobile"
                      className="h-full"
                      onSelectTarget={(path) => {
                        setMobileContextOpen(false);
                        onSelectTarget(path);
                      }}
                      onPreviewContext={() => {
                        setMobileContextOpen(false);
                        onPreviewContext();
                      }}
                    />
                  </Dialog.Popup>
                </Dialog.Viewport>
              </Dialog.Portal>
            </Dialog.Root>
            {context && (
              <p className="min-w-0 truncate font-heading text-[10px] text-muted-foreground" title={`${context.metadata.owner}/${context.metadata.name} · ${context.revision} · ${context.subdirectory ?? "repository root"} · ${selectedTargetPath || "no target"}`}>
                <span className="text-foreground">{context.metadata.owner}/{context.metadata.name}</span>
                <span aria-hidden="true"> · </span>
                <span className="tabular-nums">{context.revision.slice(0, 7)}</span>
                <span aria-hidden="true"> · </span>
                <span>{context.subdirectory ?? "repository root"}</span>
                <span aria-hidden="true"> · </span>
                <span className="text-primary">{selectedTargetPath || "no target selected"}</span>
              </p>
            )}
          </div>

          <main id="main-content" tabIndex={-1} className="terminal-grid min-h-0 flex-1 scroll-mt-24 overflow-y-auto p-4 md:p-8">
            {children}
          </main>
        </div>
      </div>
    </div>
  );
}
