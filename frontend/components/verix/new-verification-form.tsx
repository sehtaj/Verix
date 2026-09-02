"use client";

import { useEffect, type FormEvent } from "react";
import { Download, FolderGit2, GitBranch, Link2, LoaderCircle, LockKeyhole, PlusSquare, ShieldCheck } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

type NewVerificationFormProps = {
  repositoryUrl: string;
  repositoryReference: string;
  repositorySubdirectory: string;
  isLoading: boolean;
  error: string | null;
  errorField: "url" | "reference" | "subdirectory" | null;
  onRepositoryUrlChange: (value: string) => void;
  onRepositoryReferenceChange: (value: string) => void;
  onRepositorySubdirectoryChange: (value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
};

export function NewVerificationForm({
  repositoryUrl,
  repositoryReference,
  repositorySubdirectory,
  isLoading,
  error,
  errorField,
  onRepositoryUrlChange,
  onRepositoryReferenceChange,
  onRepositorySubdirectoryChange,
  onSubmit,
}: NewVerificationFormProps) {
  useEffect(() => {
    if (!error || isLoading) return;
    const fieldId = {
      url: "repository-url",
      reference: "repository-reference",
      subdirectory: "repository-subdirectory",
    }[errorField ?? "url"];
    document.getElementById(errorField ? fieldId : "repository-form-error")?.focus();
  }, [error, errorField, isLoading]);

  const inlineError = (field: NonNullable<NewVerificationFormProps["errorField"]>) =>
    error && errorField === field ? (
      <p id={`repository-${field}-error`} className="mt-2 text-sm text-destructive" role="alert">
        {error}
      </p>
    ) : null;

  return (
    <section className="mx-auto w-full max-w-4xl">
      <div className="mb-8">
        <div className="flex items-center gap-3">
          <PlusSquare className="size-8 text-primary" aria-hidden="true" />
          <h1 className="font-heading text-3xl font-bold tracking-[-0.03em] text-primary md:text-[2rem]">
            Start a New Verification
          </h1>
        </div>
        <p className="mt-2 max-w-3xl text-lg text-muted-foreground">
          Connect a public Python repository to inspect its context, run tests, and collect verification evidence.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-[280px_minmax(0,1fr)]">
        <div className="space-y-3">
          <div className="border border-primary bg-surface-high p-4">
            <div className="flex items-center justify-between gap-3 font-heading text-sm font-bold uppercase text-primary">
              <span>1. Repository Connection</span>
              <span aria-hidden="true">›</span>
            </div>
            <p className="mt-2 text-muted-foreground">Configure the target codebase and revision.</p>
          </div>
          <div className="border border-dashed border-outline-variant bg-surface-low p-4 text-muted-foreground">
            <div className="flex items-center justify-between gap-3 font-heading text-sm font-bold uppercase">
              <span>2. Security & Context</span>
              <LockKeyhole className="size-4" aria-hidden="true" />
            </div>
            <p className="mt-2">Review the selected files and isolation boundaries after fetching.</p>
          </div>
        </div>

        <form onSubmit={onSubmit} className="border border-dashed border-outline-variant bg-surface terminal-scanlines">
          <div className="border-b border-dashed border-outline-variant bg-surface-high p-4">
            <div className="flex items-center gap-3 font-heading text-sm font-bold uppercase">
              <FolderGit2 className="size-5 text-primary" aria-hidden="true" />
              <span>Module 1</span>
              <span className="text-outline" aria-hidden="true">›</span>
              <span>Repository Connection</span>
            </div>
            <p className="ml-8 mt-1 text-muted-foreground">Provide the URL and optional targeting details.</p>
          </div>

          <div className="space-y-5 p-5 md:p-6">
            <div className="border border-dashed border-outline-variant bg-surface-lowest p-4">
              <label htmlFor="repository-url" className="mb-2 flex items-center gap-2 font-heading text-xs font-bold uppercase tracking-[0.1em] text-primary">
                <Link2 className="size-4" aria-hidden="true" /> Repository URL
              </label>
              <Input
                id="repository-url"
                name="repository-url"
                type="url"
                required
                autoComplete="off"
                spellCheck={false}
                aria-invalid={errorField === "url"}
                aria-describedby={errorField === "url" ? "repository-url-hint repository-url-error" : "repository-url-hint"}
                value={repositoryUrl}
                onChange={(event) => onRepositoryUrlChange(event.target.value)}
                placeholder="https://github.com/owner/repository…"
                disabled={isLoading}
              />
              <p id="repository-url-hint" className="mt-2 text-sm text-muted-foreground">Public GitHub repositories are currently supported.</p>
              {inlineError("url")}
            </div>

            <div className="border border-dashed border-outline-variant bg-surface-lowest p-4">
              <label htmlFor="repository-reference" className="mb-2 flex items-center gap-2 font-heading text-xs font-bold uppercase tracking-[0.1em] text-primary">
                <GitBranch className="size-4" aria-hidden="true" /> Revision <span className="text-muted-foreground">(Optional)</span>
              </label>
              <Input
                id="repository-reference"
                name="repository-reference"
                autoComplete="off"
                spellCheck={false}
                aria-invalid={errorField === "reference"}
                aria-describedby={errorField === "reference" ? "repository-reference-hint repository-reference-error" : "repository-reference-hint"}
                value={repositoryReference}
                onChange={(event) => onRepositoryReferenceChange(event.target.value)}
                placeholder="Default branch…"
                disabled={isLoading}
              />
              <p id="repository-reference-hint" className="mt-2 text-sm text-muted-foreground">Enter a branch, tag, or full commit SHA, or leave blank.</p>
              {inlineError("reference")}
            </div>

            <div className="border border-dashed border-outline-variant bg-surface-lowest p-4">
              <label htmlFor="repository-subdirectory" className="mb-2 flex items-center gap-2 font-heading text-xs font-bold uppercase tracking-[0.1em] text-primary">
                <FolderGit2 className="size-4" aria-hidden="true" /> Project Folder <span className="text-muted-foreground">(Optional)</span>
              </label>
              <Input
                id="repository-subdirectory"
                name="repository-subdirectory"
                autoComplete="off"
                spellCheck={false}
                aria-invalid={errorField === "subdirectory"}
                aria-describedby={errorField === "subdirectory" ? "repository-subdirectory-hint repository-subdirectory-error" : "repository-subdirectory-hint"}
                value={repositorySubdirectory}
                onChange={(event) => onRepositorySubdirectoryChange(event.target.value)}
                placeholder="packages/payments…"
                disabled={isLoading}
              />
              <p id="repository-subdirectory-hint" className="mt-2 text-sm text-muted-foreground">Use a repository-relative folder for a nested Python project.</p>
              {inlineError("subdirectory")}
            </div>

            {error && errorField === null && (
              <p id="repository-form-error" tabIndex={-1} className="border border-destructive bg-destructive/10 p-3 text-sm text-destructive" role="alert">
                {error}
              </p>
            )}

            <div className="flex flex-col-reverse items-stretch gap-4 border-t border-dashed border-outline-variant pt-5 sm:flex-row sm:items-center sm:justify-between">
              <p className="flex max-w-md items-start gap-2 text-xs text-muted-foreground">
                <ShieldCheck className="mt-0.5 size-4 shrink-0 text-success" aria-hidden="true" />
                Fetching inspects bounded public metadata and paths. It does not run repository code or contact Gemini.
              </p>
              <Button type="submit" size="lg" disabled={isLoading}>
                {isLoading ? <LoaderCircle className="animate-spin" /> : <Download />}
                {isLoading ? "Fetching Repository…" : "Fetch Repository"}
              </Button>
            </div>
          </div>
        </form>
      </div>
    </section>
  );
}
