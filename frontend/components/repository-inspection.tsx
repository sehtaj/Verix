import type {
  RepositoryGenerationContextPreview,
  RepositoryMetadata,
  RepositoryTestPlan,
  RepositoryTree,
} from "../types/api";

function BoundedFilePreview({
  path,
  content,
  byteCount,
  open = false,
}: {
  path: string;
  content: string;
  byteCount?: number;
  open?: boolean;
}) {
  return (
    <details className="context-file" open={open}>
      <summary>
        <code>{path}</code>
        {byteCount !== undefined && <span>{byteCount} bytes</span>}
      </summary>
      <pre>{content || "Empty file."}</pre>
    </details>
  );
}

export function RepositorySummary({
  repository,
}: {
  repository: RepositoryMetadata;
}) {
  return (
    <section className="result">
      <h2>Selected repository</h2>
      <p>
        <a href={repository.url} rel="noreferrer" target="_blank">
          {repository.owner}/{repository.name}
        </a>
      </p>
      <p>{repository.description ?? "No description provided."}</p>
      <p>Primary language: {repository.language ?? "Not specified"}</p>
      <p>Stars: {repository.stars}</p>
    </section>
  );
}

export function RepositoryTreeView({ tree }: { tree: RepositoryTree }) {
  return (
    <section className="result">
      <h2>Repository file structure</h2>
      <p className="field-hint">
        {tree.is_truncated
          ? `Showing the first ${tree.entries.length} entries.`
          : `${tree.entries.length} entries.`}
      </p>
      <ul className="file-tree">
        {tree.entries.map((entry) => (
          <li
            key={`${entry.type}-${entry.path}`}
            style={{ paddingLeft: `${entry.path.split("/").length - 1}rem` }}
          >
            <span aria-hidden="true">{entry.type === "tree" ? "📁" : "📄"}</span>{" "}
            {entry.path}
          </li>
        ))}
      </ul>
    </section>
  );
}

type RepositoryContextPreviewProps = {
  sourcePaths: string[];
  selectedTargetPath: string;
  preview: RepositoryGenerationContextPreview | null;
  isLoading: boolean;
  isDisabled: boolean;
  error: string | null;
  onTargetChange: (targetPath: string) => void;
  onPreview: () => void;
};

export function RepositoryContextPreview({
  sourcePaths,
  selectedTargetPath,
  preview,
  isLoading,
  isDisabled,
  error,
  onTargetChange,
  onPreview,
}: RepositoryContextPreviewProps) {
  return (
    <section className="result context-preview">
      <h2>Gemini context preview</h2>
      <p>
        Choose one verified Python source file, then inspect the bounded evidence Verix could send
        to Gemini. Previewing does not call Gemini or run repository code.
      </p>
      <label htmlFor="repository-target">Python source target</label>
      <select
        id="repository-target"
        name="repository-target"
        value={selectedTargetPath}
        disabled={isDisabled || isLoading || sourcePaths.length === 0}
        onChange={(event) => onTargetChange(event.target.value)}
      >
        {sourcePaths.length === 0 && <option value="">No Python source files found</option>}
        {sourcePaths.map((path) => (
          <option key={path} value={path}>
            {path}
          </option>
        ))}
      </select>
      <p className="field-hint">
        The file must be inside the selected project folder at the resolved commit.
      </p>
      <button
        disabled={isDisabled || isLoading || !selectedTargetPath}
        onClick={onPreview}
        type="button"
      >
        {isLoading ? "Loading context preview..." : "Preview Gemini context"}
      </button>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {preview !== null && (
        <div className="context-preview-result" aria-live="polite">
          <dl className="plan-summary">
            <div>
              <dt>Resolved commit</dt>
              <dd className="revision-value">{preview.revision}</dd>
            </div>
            <div>
              <dt>Selected project folder</dt>
              <dd>{preview.subdirectory ?? "Repository root"}</dd>
            </div>
            <div>
              <dt>Included context size</dt>
              <dd>{preview.total_bytes} bytes</dd>
            </div>
            <div>
              <dt>Related test files</dt>
              <dd>{preview.test_files.length}</dd>
            </div>
          </dl>

          {preview.skipped_paths.length > 0 && (
            <div className="context-skipped warning">
              <p>These optional files were skipped because of the context size limits:</p>
              <ul>
                {preview.skipped_paths.map((path) => (
                  <li key={path}>{path}</li>
                ))}
              </ul>
            </div>
          )}

          <h3>Selected source</h3>
          {preview.source_file !== null && (
            <BoundedFilePreview
              path={preview.source_file.path}
              content={preview.source_file.content}
              byteCount={preview.source_file.byte_count}
              open
            />
          )}

          <h3>Related existing tests</h3>
          {preview.test_files.length === 0 ? (
            <p>No related existing test files were included.</p>
          ) : (
            preview.test_files.map((file) => (
              <BoundedFilePreview
                key={file.path}
                path={file.path}
                content={file.content}
                byteCount={file.byte_count}
              />
            ))
          )}

          <h3>Project configuration</h3>
          {preview.configuration_files.length === 0 ? (
            <p>No project configuration files were included.</p>
          ) : (
            preview.configuration_files.map((file) => (
              <BoundedFilePreview key={file.path} path={file.path} content={file.content} />
            ))
          )}
        </div>
      )}
    </section>
  );
}

type RepositoryTestPlanPanelProps = {
  plan: RepositoryTestPlan;
  isRepositoryLoading: boolean;
  isRepositoryTestRunning: boolean;
  isRepositoryGenerationRunning: boolean;
  isRepositoryInvestigationRunning: boolean;
  isRepositoryFixProposalRunning: boolean;
  isRepositoryFixVerificationRunning: boolean;
  repositoryTestError: string | null;
  repositoryGenerationError: string | null;
  repositoryInvestigationError: string | null;
  repositoryFixProposalError: string | null;
  onRunRepositoryTests: () => void;
  onGenerateRepositoryTests: () => void;
  onInvestigateRepository: () => void;
  onProposeRepositoryFix: () => void;
};

export function RepositoryTestPlanPanel({
  plan,
  isRepositoryLoading,
  isRepositoryTestRunning,
  isRepositoryGenerationRunning,
  isRepositoryInvestigationRunning,
  isRepositoryFixProposalRunning,
  isRepositoryFixVerificationRunning,
  repositoryTestError,
  repositoryGenerationError,
  repositoryInvestigationError,
  repositoryFixProposalError,
  onRunRepositoryTests,
  onGenerateRepositoryTests,
  onInvestigateRepository,
  onProposeRepositoryFix,
}: RepositoryTestPlanPanelProps) {
  return (
    <section className="result">
      <h2>Repository test plan</h2>
      <dl className="plan-summary">
        <div>
          <dt>Python project</dt>
          <dd>{plan.setup.is_python_project ? "Yes" : "Not detected"}</dd>
        </div>
        <div>
          <dt>Project tool</dt>
          <dd>{plan.setup.project_tool ?? "Not detected"}</dd>
        </div>
        <div>
          <dt>Test runner</dt>
          <dd>{plan.setup.test_runner ?? "Not detected"}</dd>
        </div>
        <div>
          <dt>Likely source files</dt>
          <dd>{plan.source_paths.length}</dd>
        </div>
        <div>
          <dt>Existing test files</dt>
          <dd>{plan.test_paths.length}</dd>
        </div>
      </dl>
      {plan.is_truncated && (
        <p className="warning">The repository tree is incomplete, so this plan may miss files.</p>
      )}
      <ol className="test-plan">
        {plan.steps.map((step) => (
          <li key={step.action}>
            <strong>{step.action.replaceAll("_", " ")}</strong>
            <p>{step.description}</p>
            {step.command && <code>{step.command}</code>}
          </li>
        ))}
      </ol>
      <div className="test-run-action">
        <p>
          Run the repository&apos;s existing tests in Docker. Dependencies may be downloaded during
          setup; test execution itself has no network access.
        </p>
        <button
          disabled={
            isRepositoryTestRunning ||
            isRepositoryLoading ||
            isRepositoryGenerationRunning
            || isRepositoryInvestigationRunning ||
            isRepositoryFixProposalRunning ||
            isRepositoryFixVerificationRunning
          }
          onClick={onRunRepositoryTests}
          type="button"
        >
          {isRepositoryTestRunning ? "Running repository tests..." : "Run repository tests"}
        </button>
        {repositoryTestError && (
          <p className="error" role="alert">
            {repositoryTestError}
          </p>
        )}
      </div>
      <div className="test-run-action">
        <p>
          Ask Gemini to create focused pytest tests for one selected source file, then run the
          original and generated tests separately in Docker.
        </p>
        <button
          disabled={
            isRepositoryGenerationRunning ||
            isRepositoryLoading ||
            isRepositoryTestRunning
            || isRepositoryInvestigationRunning ||
            isRepositoryFixProposalRunning ||
            isRepositoryFixVerificationRunning
          }
          onClick={onGenerateRepositoryTests}
          type="button"
        >
          {isRepositoryGenerationRunning
            ? "Generating and running tests..."
            : "Generate repository tests"}
        </button>
        {repositoryGenerationError && (
          <p className="error" role="alert">
            {repositoryGenerationError}
          </p>
        )}
      </div>
      <div className="test-run-action">
        <p>
          Generate focused tests, run both test suites in Docker, then get a Gemini explanation
          grounded in the recorded execution results.
        </p>
        <button
          disabled={
            isRepositoryInvestigationRunning ||
            isRepositoryLoading ||
            isRepositoryTestRunning ||
            isRepositoryGenerationRunning ||
            isRepositoryFixProposalRunning ||
            isRepositoryFixVerificationRunning
          }
          onClick={onInvestigateRepository}
          type="button"
        >
          {isRepositoryInvestigationRunning
            ? "Investigating repository..."
            : "Investigate repository"}
        </button>
        {repositoryInvestigationError && (
          <p className="error" role="alert">
            {repositoryInvestigationError}
          </p>
        )}
      </div>
      <div className="test-run-action">
        <p>
          Run one investigation, then ask Gemini for one validated source-only patch. The patch is
          shown for review and is never applied automatically.
        </p>
        <button
          disabled={
            isRepositoryFixProposalRunning ||
            isRepositoryLoading ||
            isRepositoryTestRunning ||
            isRepositoryGenerationRunning ||
            isRepositoryInvestigationRunning ||
            isRepositoryFixVerificationRunning
          }
          onClick={onProposeRepositoryFix}
          type="button"
        >
          {isRepositoryFixProposalRunning
            ? "Investigating and proposing a fix..."
            : "Propose source fix"}
        </button>
        {repositoryFixProposalError && (
          <p className="error" role="alert">
            {repositoryFixProposalError}
          </p>
        )}
      </div>
    </section>
  );
}
