import type {
  RepositoryExecution,
  RepositoryGenerationRun,
  RepositoryTestRun,
} from "../types/api";

function executionStatusClass(execution: RepositoryExecution): string {
  if (execution.skipped) {
    return "execution-status skipped";
  }
  if (execution.timed_out || execution.return_code !== 0) {
    return "execution-status failed";
  }
  return "execution-status passed";
}

export function RepositoryTestRunResult({ result }: { result: RepositoryTestRun }) {
  return (
    <section className="result repository-test-result" aria-live="polite">
      <h2>Repository test execution</h2>
      <dl className="plan-summary">
        <div>
          <dt>Test runner</dt>
          <dd>{result.test_runner}</dd>
        </div>
        <div>
          <dt>Prepared files</dt>
          <dd>{result.preparation.file_count}</dd>
        </div>
        <div>
          <dt>Prepared size</dt>
          <dd>{result.preparation.total_bytes} bytes</dd>
        </div>
        <div>
          <dt>Skipped archive entries</dt>
          <dd>{result.preparation.skipped_entries}</dd>
        </div>
      </dl>

      <h3>Dependency installation</h3>
      <p className={executionStatusClass(result.installation)} role="status">
        {result.installation.skipped
          ? "No dependency installation was required."
          : result.installation.timed_out
            ? "Dependency installation timed out."
            : result.installation.return_code === 0
              ? "Dependencies prepared successfully."
              : "Dependency installation failed."}
      </p>
      <pre>{result.installation.output || "No installation output."}</pre>

      <h3>Existing test suite</h3>
      <p className={executionStatusClass(result.execution)} role="status">
        {result.execution.skipped
          ? "Test execution was skipped."
          : result.execution.timed_out
            ? "Repository tests timed out."
            : result.execution.return_code === 0
              ? "Repository tests passed."
              : "Repository tests failed."}
      </p>
      <pre>{result.execution.output || "No test output."}</pre>
    </section>
  );
}

export function RepositoryGenerationResult({
  result,
}: {
  result: RepositoryGenerationRun;
}) {
  return (
    <section className="result repository-test-result" aria-live="polite">
      <h2>Generated repository tests</h2>
      <p>
        Selected source: <code>{result.target_path}</code>
      </p>
      <dl className="plan-summary">
        <div>
          <dt>Existing test runner</dt>
          <dd>{result.test_runner}</dd>
        </div>
        <div>
          <dt>Prepared files</dt>
          <dd>{result.preparation.file_count}</dd>
        </div>
        <div>
          <dt>Prepared size</dt>
          <dd>{result.preparation.total_bytes} bytes</dd>
        </div>
        <div>
          <dt>Skipped archive entries</dt>
          <dd>{result.preparation.skipped_entries}</dd>
        </div>
      </dl>

      <h3>Generated pytest code</h3>
      <pre>{result.generated_tests}</pre>

      <h3>Dependency installation</h3>
      <p className={executionStatusClass(result.installation)} role="status">
        {result.installation.skipped
          ? "No dependency installation was required."
          : result.installation.timed_out
            ? "Dependency installation timed out."
            : result.installation.return_code === 0
              ? "Dependencies prepared successfully."
              : "Dependency installation failed."}
      </p>
      <pre>{result.installation.output || "No installation output."}</pre>

      <h3>Original repository test suite</h3>
      <p className={executionStatusClass(result.existing_execution)} role="status">
        {result.existing_execution.skipped
          ? "Original repository tests were skipped."
          : result.existing_execution.timed_out
            ? "Original repository tests timed out."
            : result.existing_execution.return_code === 0
              ? "Original repository tests passed."
              : "Original repository tests failed."}
      </p>
      <pre>{result.existing_execution.output || "No original test output."}</pre>

      <h3>Verix-generated test suite</h3>
      <p className={executionStatusClass(result.generated_execution)} role="status">
        {result.generated_execution.skipped
          ? "Generated tests were skipped."
          : result.generated_execution.timed_out
            ? "Generated tests timed out."
            : result.generated_execution.return_code === 0
              ? "Generated tests passed."
              : "Generated tests failed."}
      </p>
      <pre>{result.generated_execution.output || "No generated test output."}</pre>
    </section>
  );
}
