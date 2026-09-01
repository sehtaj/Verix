"use client";

import { useEffect, useState } from "react";
import { Archive, Eye, File, FileCode2, Folder, LoaderCircle, RefreshCw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { RepositoryContext } from "@/types/api";

type RepositorySidebarProps = {
  context: RepositoryContext | null;
  selectedTargetPath: string;
  isBusy: boolean;
  isPreviewDisabled: boolean;
  isPreviewLoading: boolean;
  previewError: string | null;
  onSelectTarget: (path: string) => void;
  onPreviewContext: () => void;
  className?: string;
  id?: string;
};

export function RepositorySidebar({
  context,
  selectedTargetPath,
  isBusy,
  isPreviewDisabled,
  isPreviewLoading,
  previewError,
  onSelectTarget,
  onPreviewContext,
  className,
  id = "repository-context",
}: RepositorySidebarProps) {
  const [visibleLimit, setVisibleLimit] = useState(100);
  const sourcePaths = new Set(context?.test_plan.source_paths ?? []);
  const testPaths = new Set(context?.test_plan.test_paths ?? []);
  const entries = context?.tree.entries ?? [];
  const selectedIndex = entries.findIndex((entry) => entry.path === selectedTargetPath);
  const effectiveLimit = Math.max(visibleLimit, selectedIndex + 1);
  const visibleEntries = entries.slice(0, effectiveLimit);
  const remainingEntries = Math.max(0, entries.length - effectiveLimit);

  useEffect(() => {
    setVisibleLimit(100);
  }, [context?.revision, context?.subdirectory]);

  return (
    <aside
      id={id}
      tabIndex={-1}
      className={cn("flex min-h-0 flex-col bg-surface-low", className)}
      aria-label="Repository context"
    >
      <div className="flex h-[53px] shrink-0 items-center justify-between border-b border-dashed border-outline-variant px-4">
        <h2 className="font-heading text-xs font-bold uppercase tracking-[0.1em]">
          Repository Context
        </h2>
        <RefreshCw className={cn("size-4 text-muted-foreground", (isBusy || isPreviewLoading) && "animate-spin")} aria-hidden="true" />
      </div>

      {context === null ? (
        <div className="flex flex-1 flex-col items-center justify-center gap-4 px-6 text-center">
          <Archive className="size-9 text-muted-foreground" aria-hidden="true" />
          <p className="font-heading text-sm text-foreground">No context loaded.</p>
          <p className="text-sm text-muted-foreground">Connect a repository to begin.</p>
        </div>
      ) : (
        <>
          <div className="min-h-0 flex-1 overflow-y-auto px-2 py-3">
            <ul className="space-y-0.5" aria-label="Bounded repository tree">
              {visibleEntries.map((entry) => {
                const depth = Math.max(0, entry.path.split("/").length - 1);
                const isDirectory = entry.type === "tree";
                const isSource = sourcePaths.has(entry.path);
                const isTest = testPaths.has(entry.path);
                const isSelected = entry.path === selectedTargetPath;
                const Icon = isDirectory ? Folder : isSource || isTest ? FileCode2 : File;
                const row = (
                  <>
                    <Icon
                      className={cn(
                        "size-3.5 shrink-0",
                        isSelected ? "text-primary" : isTest ? "text-success" : "text-muted-foreground",
                      )}
                      aria-hidden="true"
                    />
                    <span className="truncate" title={entry.path}>
                      {entry.path.split("/").at(-1)}
                    </span>
                  </>
                );

                return (
                  <li className="content-auto" key={`${entry.type}:${entry.path}`} style={{ paddingLeft: `${depth * 12}px` }}>
                    {isSource ? (
                      <button
                        type="button"
                        disabled={isBusy}
                        aria-pressed={isSelected}
                        onClick={() => onSelectTarget(entry.path)}
                        className={cn(
                          "flex w-full items-center gap-2 border border-transparent px-2 py-1.5 text-left font-heading text-xs text-foreground hover:border-outline-variant hover:bg-surface",
                          isSelected && "border-primary bg-surface-high text-primary",
                        )}
                      >
                        {row}
                      </button>
                    ) : (
                      <div className="flex items-center gap-2 px-2 py-1.5 font-heading text-xs text-foreground/85">
                        {row}
                      </div>
                    )}
                  </li>
                );
              })}
            </ul>

            {remainingEntries > 0 && (
              <Button
                className="mt-3 w-full"
                size="sm"
                variant="ghost"
                onClick={() => setVisibleLimit((limit) => limit + 100)}
              >
                Show {Math.min(100, remainingEntries)} More Entries
              </Button>
            )}

            {context.tree.is_truncated && (
              <p className="m-2 border border-dashed border-primary/50 bg-primary/5 p-2 text-xs text-primary">
                The repository tree is bounded. Some paths may not be shown.
              </p>
            )}
          </div>

          <div className="shrink-0 border-t border-dashed border-outline-variant p-4">
            <Button
              className="w-full"
              variant="outline"
              disabled={!selectedTargetPath || isPreviewDisabled}
              onClick={onPreviewContext}
            >
              {isPreviewLoading ? <LoaderCircle className="animate-spin" /> : <Eye />}
              {isPreviewLoading ? "Preparing Preview…" : "Preview Context"}
            </Button>
            {previewError && (
              <p className="mt-3 text-xs text-destructive" role="alert">
                {previewError}
              </p>
            )}
          </div>
        </>
      )}
    </aside>
  );
}
