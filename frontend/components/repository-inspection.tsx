import type {
  RepositoryMetadata,
  RepositoryTestPlan,
  RepositoryTree,
} from "../types/api";

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

type RepositoryTestPlanPanelProps = {
  plan: RepositoryTestPlan;
  isRepositoryLoading: boolean;
  isRepositoryTestRunning: boolean;
  isRepositoryGenerationRunning: boolean;
  isRepositoryInvestigationRunning: boolean;
  repositoryTestError: string | null;
  repositoryGenerationError: string | null;
  repositoryInvestigationError: string | null;
  onRunRepositoryTests: () => void;
  onGenerateRepositoryTests: () => void;
  onInvestigateRepository: () => void;
};

export function RepositoryTestPlanPanel({
  plan,
  isRepositoryLoading,
  isRepositoryTestRunning,
  isRepositoryGenerationRunning,
  isRepositoryInvestigationRunning,
  repositoryTestError,
  repositoryGenerationError,
  repositoryInvestigationError,
  onRunRepositoryTests,
  onGenerateRepositoryTests,
  onInvestigateRepository,
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
            || isRepositoryInvestigationRunning
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
            || isRepositoryInvestigationRunning
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
            isRepositoryGenerationRunning
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
    </section>
  );
}
