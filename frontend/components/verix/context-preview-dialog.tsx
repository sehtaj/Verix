"use client";

import { Dialog } from "@base-ui/react/dialog";
import { FileCode2, LoaderCircle, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import type { RepositoryGenerationContextPreview } from "@/types/api";

const numberFormatter = new Intl.NumberFormat();

type ContextPreviewDialogProps = {
  preview: RepositoryGenerationContextPreview | null;
  isLoading: boolean;
  error: string | null;
  onClose: () => void;
};

function PreviewFile({ path, content }: { path: string; content: string }) {
  return (
    <section className="border border-dashed border-outline-variant bg-surface-lowest">
      <h3 className="flex items-center gap-2 border-b border-dashed border-outline-variant px-4 py-3 font-heading text-xs text-primary">
        <FileCode2 className="size-4" aria-hidden="true" />
        <span className="path-text">{path}</span>
      </h3>
      <pre
        tabIndex={0}
        aria-label={`Contents of ${path}`}
        className="max-h-72 overflow-auto whitespace-pre p-4 font-heading text-xs leading-5 text-foreground"
      >
        <code>{content}</code>
      </pre>
    </section>
  );
}

export function ContextPreviewDialog({
  preview,
  isLoading,
  error,
  onClose,
}: ContextPreviewDialogProps) {
  const open = isLoading || preview !== null || error !== null;

  return (
    <Dialog.Root open={open} onOpenChange={(nextOpen) => !nextOpen && onClose()}>
      <Dialog.Portal>
        <Dialog.Backdrop className="fixed inset-0 z-[70] bg-black/80" />
        <Dialog.Viewport className="dialog-safe fixed inset-0 z-[71] grid place-items-center overflow-y-auto overscroll-contain p-4">
          <Dialog.Popup className="my-8 w-full max-w-5xl border border-outline bg-surface outline-none focus-visible:ring-2 focus-visible:ring-primary">
            <header className="flex items-start justify-between gap-4 border-b border-dashed border-outline-variant p-5">
              <div>
                <Dialog.Title className="font-heading text-lg font-bold text-primary">
                  Bounded Context Preview
                </Dialog.Title>
                <Dialog.Description className="mt-1 text-sm text-muted-foreground">
                  This is the exact bounded repository content that would be available to Gemini for a later generation action. Previewing runs no repository code and does not contact Gemini.
                </Dialog.Description>
              </div>
              <Dialog.Close
                aria-label="Close context preview"
                className="grid size-9 shrink-0 place-items-center border border-outline bg-surface-low hover:border-primary hover:text-primary"
              >
                <X className="size-4" aria-hidden="true" />
              </Dialog.Close>
            </header>

            <div
              tabIndex={0}
              aria-label="Context preview content"
              className="max-h-[75vh] space-y-4 overflow-y-auto p-5"
            >
              {isLoading && (
                <div className="flex min-h-64 flex-col items-center justify-center gap-4 text-center">
                  <LoaderCircle className="size-8 animate-spin text-primary" aria-hidden="true" />
                  <p className="font-heading text-sm">Preparing bounded context…</p>
                </div>
              )}

              {error && (
                <div className="border border-destructive bg-destructive/5 p-4 text-sm text-destructive" role="alert">
                  {error}
                </div>
              )}

              {preview && (
                <>
                  <p className="sr-only" role="status" aria-live="polite">
                    Context preview ready with {numberFormatter.format(preview.total_bytes)} bytes.
                  </p>
                  <dl className="grid gap-px border border-outline-variant bg-outline-variant sm:grid-cols-3">
                    <div className="bg-surface-low p-3">
                      <dt className="font-heading text-[10px] uppercase text-muted-foreground">Revision</dt>
                      <dd className="path-text mt-1 text-sm">{preview.revision}</dd>
                    </div>
                    <div className="bg-surface-low p-3">
                      <dt className="font-heading text-[10px] uppercase text-muted-foreground">Total Context</dt>
                      <dd className="mt-1 text-sm tabular-nums">{numberFormatter.format(preview.total_bytes)} bytes</dd>
                    </div>
                    <div className="bg-surface-low p-3">
                      <dt className="font-heading text-[10px] uppercase text-muted-foreground">Files</dt>
                      <dd className="mt-1 text-sm">
                        {(preview.source_file ? 1 : 0) + preview.documentation_files.length + preview.test_files.length + preview.configuration_files.length}
                      </dd>
                    </div>
                  </dl>

                  {preview.source_file && <PreviewFile {...preview.source_file} />}
                  {preview.documentation_files.length > 0 && (
                    <section className="space-y-3">
                      <h3 className="font-heading text-xs uppercase text-muted-foreground">Behavior documentation</h3>
                      {preview.documentation_files.map((file) => <PreviewFile key={file.path} {...file} />)}
                    </section>
                  )}
                  {preview.test_files.map((file) => <PreviewFile key={file.path} {...file} />)}
                  {preview.configuration_files.map((file) => <PreviewFile key={file.path} {...file} />)}

                  {preview.skipped_paths.length > 0 && (
                    <section className="border border-dashed border-outline-variant p-4">
                      <h3 className="font-heading text-xs uppercase text-muted-foreground">Skipped paths</h3>
                      <ul className="mt-2 space-y-1 font-heading text-xs text-muted-foreground">
                        {preview.skipped_paths.map((path) => <li className="path-text" key={path}>{path}</li>)}
                      </ul>
                    </section>
                  )}
                </>
              )}
            </div>

            <footer className="flex justify-end border-t border-dashed border-outline-variant p-4">
              <Button variant="outline" onClick={onClose}>Close Preview</Button>
            </footer>
          </Dialog.Popup>
        </Dialog.Viewport>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
