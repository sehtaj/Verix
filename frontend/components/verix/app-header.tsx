"use client";

import {
  Bell,
  CircleHelp,
  FileCode2,
  FolderGit2,
  FolderTree,
  GitBranch,
  Plus,
  UserRound,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import type { RepositoryContext } from "@/types/api";

type AppHeaderProps = {
  context: RepositoryContext | null;
  selectedTargetPath: string;
  isBusy: boolean;
  onNewVerification: () => void;
};

export function AppHeader({ context, selectedTargetPath, isBusy, onNewVerification }: AppHeaderProps) {
  const repositoryLabel = context
    ? `${context.metadata.owner}/${context.metadata.name}`
    : "No Repository Selected";

  return (
    <header className="app-header fixed inset-x-0 top-0 z-50 flex items-center border-b border-dashed border-outline-variant bg-surface-low px-4 md:px-8">
      <div className="flex min-w-0 flex-1 items-center gap-4 xl:gap-8">
        <button
          type="button"
          className="shrink-0 font-heading text-2xl font-bold tracking-[-0.04em] text-primary hover:text-primary-strong"
          aria-label="Start a new verification"
          disabled={isBusy}
          onClick={onNewVerification}
        >
          Verix
        </button>

        <div
          className="hidden min-w-0 items-center gap-2 border border-dashed border-outline-variant px-3 py-1.5 font-heading text-sm lg:flex"
          title={repositoryLabel}
        >
          <FolderGit2 className="size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
          <span className="max-w-44 truncate">{repositoryLabel}</span>
          {context && (
            <>
              <span className="text-outline" aria-hidden="true">·</span>
              <GitBranch className="size-3.5 shrink-0 text-muted-foreground" aria-hidden="true" />
              <span className="max-w-24 truncate tabular-nums" title={context.revision}>
                {context.revision.slice(0, 7)}
              </span>
              {context.subdirectory && (
                <>
                  <span className="text-outline" aria-hidden="true">·</span>
                  <FolderTree className="size-3.5 shrink-0 text-muted-foreground" aria-hidden="true" />
                  <span className="max-w-28 truncate" title={context.subdirectory}>{context.subdirectory}</span>
                </>
              )}
              {selectedTargetPath && (
                <>
                  <span className="hidden text-outline 2xl:inline" aria-hidden="true">·</span>
                  <FileCode2 className="hidden size-3.5 shrink-0 text-muted-foreground 2xl:block" aria-hidden="true" />
                  <span className="hidden max-w-36 truncate 2xl:inline" title={selectedTargetPath}>
                    {selectedTargetPath.split("/").at(-1)}
                  </span>
                </>
              )}
            </>
          )}
        </div>

        <nav aria-label="Primary" className="hidden h-16 items-center gap-6 xl:flex">
          <span aria-disabled="true" className="font-heading text-sm text-muted-foreground">
            Explorer
          </span>
          <span
            aria-current="page"
            className="flex h-16 items-center border-b-2 border-primary font-heading text-sm text-primary"
          >
            Verifications
          </span>
          <span aria-disabled="true" className="font-heading text-sm text-muted-foreground">
            Reports
          </span>
          <span aria-disabled="true" className="font-heading text-sm text-muted-foreground">
            Settings
          </span>
        </nav>
      </div>

      <div className="flex shrink-0 items-center gap-2 md:gap-3">
        <Button size="sm" variant="outline" disabled={isBusy} onClick={onNewVerification}>
          <Plus data-icon="inline-start" />
          <span className="hidden sm:inline">New Verification</span>
          <span className="sm:hidden">New</span>
        </Button>
        <span aria-label="Notifications unavailable" aria-disabled="true" className="hidden p-2 text-muted-foreground md:inline-flex">
          <Bell className="size-5" aria-hidden="true" />
        </span>
        <span aria-label="Help unavailable" aria-disabled="true" className="hidden p-2 text-muted-foreground md:inline-flex">
          <CircleHelp className="size-5" aria-hidden="true" />
        </span>
        <span aria-label="Profile unavailable" aria-disabled="true" className="hidden size-8 items-center justify-center border border-outline-variant bg-surface-high text-muted-foreground sm:inline-flex">
          <UserRound className="size-4" aria-hidden="true" />
        </span>
      </div>
    </header>
  );
}
