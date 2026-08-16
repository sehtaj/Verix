"use client";

import { FormEvent, useState } from "react";

import {
  RepositoryGenerationResult,
  RepositoryTestRunResult,
} from "../components/repository-execution-results";
import {
  fetchRepositoryContext,
  generatePastedCodeTests,
  generateRepositoryTests,
  runRepositoryTests,
} from "../lib/api";
import type {
  RepositoryGenerationRun,
  RepositoryMetadata,
  RepositoryTestPlan,
  RepositoryTestRun,
  RepositoryTree,
  TestExecution,
} from "../types/api";

function isPublicGitHubRepositoryUrl(value: string): boolean {
  try {
    const url = new URL(value);
    const pathSegments = url.pathname.split("/").filter(Boolean);

    return (
      url.protocol === "https:" &&
      url.hostname === "github.com" &&
      !url.port &&
      pathSegments.length === 2 &&
      !url.search &&
      !url.hash
    );
  } catch {
    return false;
  }
}

export default function Home() {
  const [code, setCode] = useState("");
  const [repositoryUrl, setRepositoryUrl] = useState("");
  const [repository, setRepository] = useState<RepositoryMetadata | null>(null);
  const [repositoryTree, setRepositoryTree] = useState<RepositoryTree | null>(null);
  const [repositoryTestPlan, setRepositoryTestPlan] = useState<RepositoryTestPlan | null>(null);
  const [isRepositoryLoading, setIsRepositoryLoading] = useState(false);
  const [repositoryError, setRepositoryError] = useState<string | null>(null);
  const [repositoryTestRun, setRepositoryTestRun] = useState<RepositoryTestRun | null>(null);
  const [isRepositoryTestRunning, setIsRepositoryTestRunning] = useState(false);
  const [repositoryTestError, setRepositoryTestError] = useState<string | null>(null);
  const [repositoryGenerationRun, setRepositoryGenerationRun] =
    useState<RepositoryGenerationRun | null>(null);
  const [isRepositoryGenerationRunning, setIsRepositoryGenerationRunning] = useState(false);
  const [repositoryGenerationError, setRepositoryGenerationError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [tests, setTests] = useState<string | null>(null);
  const [execution, setExecution] = useState<TestExecution | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleRepositorySubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!isPublicGitHubRepositoryUrl(repositoryUrl)) {
      setRepositoryError("Enter a public GitHub repository URL, such as https://github.com/owner/repository.");
      setRepository(null);
      setRepositoryTree(null);
      setRepositoryTestPlan(null);
      setRepositoryTestRun(null);
      setRepositoryTestError(null);
      setRepositoryGenerationRun(null);
      setRepositoryGenerationError(null);
      return;
    }

    setIsRepositoryLoading(true);
    setRepositoryError(null);
    setRepository(null);
    setRepositoryTree(null);
    setRepositoryTestPlan(null);
    setRepositoryTestRun(null);
    setRepositoryTestError(null);
    setRepositoryGenerationRun(null);
    setRepositoryGenerationError(null);

    try {
      const context = await fetchRepositoryContext(repositoryUrl);

      setRepository(context.metadata);
      setRepositoryTree(context.tree);
      setRepositoryTestPlan(context.test_plan);
    } catch (error) {
      setRepositoryError(
        error instanceof Error ? error.message : "Unable to fetch repository details. Please try again.",
      );
    } finally {
      setIsRepositoryLoading(false);
    }
  }

  async function handleRepositoryTestRun() {
    if (repository === null) {
      setRepositoryTestError("Fetch a public Python repository before running its tests.");
      return;
    }

    setIsRepositoryTestRunning(true);
    setRepositoryTestError(null);
    setRepositoryTestRun(null);
    setRepositoryGenerationError(null);
    setRepositoryGenerationRun(null);

    try {
      const result = await runRepositoryTests(repository.url);

      setRepositoryTestRun(result);
    } catch (error) {
      setRepositoryTestError(
        error instanceof Error
          ? error.message
          : "Unable to run repository tests. Please try again.",
      );
    } finally {
      setIsRepositoryTestRunning(false);
    }
  }

  async function handleRepositoryGeneration() {
    if (repository === null) {
      setRepositoryGenerationError(
        "Fetch a public Python repository before generating its tests.",
      );
      return;
    }

    setIsRepositoryGenerationRunning(true);
    setRepositoryGenerationError(null);
    setRepositoryGenerationRun(null);
    setRepositoryTestError(null);
    setRepositoryTestRun(null);

    try {
      const result = await generateRepositoryTests(repository.url);

      setRepositoryGenerationRun(result);
    } catch (error) {
      setRepositoryGenerationError(
        error instanceof Error
          ? error.message
          : "Unable to generate repository tests. Please try again.",
      );
    } finally {
      setIsRepositoryGenerationRunning(false);
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!code.trim()) {
      setError("Enter Python code before generating tests.");
      return;
    }

    setIsLoading(true);
    setError(null);
    setTests(null);
    setExecution(null);

    try {
      const result = await generatePastedCodeTests(code);
      setTests(result.tests);
      setExecution(result.execution);
    } catch {
      setError("Unable to generate tests. Please try again.");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <main>
      <section className="generator">
        <h1>Verix</h1>
        <p>Look up a public GitHub repository or generate tests for pasted Python code.</p>
        <form onSubmit={handleRepositorySubmit}>
          <label htmlFor="repository-url">GitHub repository URL</label>
          <input
            id="repository-url"
            name="repository-url"
            placeholder="https://github.com/owner/repository"
            type="url"
            value={repositoryUrl}
            disabled={
              isRepositoryLoading ||
              isRepositoryTestRunning ||
              isRepositoryGenerationRunning
            }
            onChange={(event) => setRepositoryUrl(event.target.value)}
          />
          <p className="field-hint">Use an HTTPS URL for a public repository.</p>
          <button
            disabled={
              isRepositoryLoading ||
              isRepositoryTestRunning ||
              isRepositoryGenerationRunning
            }
            type="submit"
          >
            {isRepositoryLoading ? "Fetching..." : "Fetch repository"}
          </button>
          {repositoryError && (
            <p className="error" role="alert">
              {repositoryError}
            </p>
          )}
        </form>
        {repository !== null && (
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
        )}
        {repositoryTree !== null && (
          <section className="result">
            <h2>Repository file structure</h2>
            <p className="field-hint">
              {repositoryTree.is_truncated
                ? `Showing the first ${repositoryTree.entries.length} entries.`
                : `${repositoryTree.entries.length} entries.`}
            </p>
            <ul className="file-tree">
              {repositoryTree.entries.map((entry) => (
                <li
                  key={`${entry.type}-${entry.path}`}
                  style={{ paddingLeft: `${entry.path.split("/").length - 1}rem` }}
                >
                  <span aria-hidden="true">{entry.type === "tree" ? "📁" : "📄"}</span> {entry.path}
                </li>
              ))}
            </ul>
          </section>
        )}
        {repositoryTestPlan !== null && (
          <section className="result">
            <h2>Repository test plan</h2>
            <dl className="plan-summary">
              <div>
                <dt>Python project</dt>
                <dd>{repositoryTestPlan.setup.is_python_project ? "Yes" : "Not detected"}</dd>
              </div>
              <div>
                <dt>Project tool</dt>
                <dd>{repositoryTestPlan.setup.project_tool ?? "Not detected"}</dd>
              </div>
              <div>
                <dt>Test runner</dt>
                <dd>{repositoryTestPlan.setup.test_runner ?? "Not detected"}</dd>
              </div>
              <div>
                <dt>Likely source files</dt>
                <dd>{repositoryTestPlan.source_paths.length}</dd>
              </div>
              <div>
                <dt>Existing test files</dt>
                <dd>{repositoryTestPlan.test_paths.length}</dd>
              </div>
            </dl>
            {repositoryTestPlan.is_truncated && (
              <p className="warning">The repository tree is incomplete, so this plan may miss files.</p>
            )}
            <ol className="test-plan">
              {repositoryTestPlan.steps.map((step) => (
                <li key={step.action}>
                  <strong>{step.action.replaceAll("_", " ")}</strong>
                  <p>{step.description}</p>
                  {step.command && <code>{step.command}</code>}
                </li>
              ))}
            </ol>
            <div className="test-run-action">
              <p>
                Run the repository&apos;s existing tests in Docker. Dependencies may be downloaded
                during setup; test execution itself has no network access.
              </p>
              <button
                disabled={
                  isRepositoryTestRunning ||
                  isRepositoryLoading ||
                  isRepositoryGenerationRunning
                }
                onClick={handleRepositoryTestRun}
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
                Ask Gemini to create focused pytest tests for one selected source file, then run
                the original and generated tests separately in Docker.
              </p>
              <button
                disabled={
                  isRepositoryGenerationRunning ||
                  isRepositoryLoading ||
                  isRepositoryTestRunning
                }
                onClick={handleRepositoryGeneration}
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
          </section>
        )}
        {repositoryTestRun !== null && (
          <RepositoryTestRunResult result={repositoryTestRun} />
        )}
        {repositoryGenerationRun !== null && (
          <RepositoryGenerationResult result={repositoryGenerationRun} />
        )}
        <form className="code-generator" onSubmit={handleSubmit}>
          <label htmlFor="code">Python code</label>
          <textarea
            id="code"
            name="code"
            placeholder="def add(a, b):\n    return a + b"
            rows={12}
            value={code}
            onChange={(event) => setCode(event.target.value)}
          />
          <button disabled={isLoading} type="submit">
            {isLoading ? "Generating..." : "Generate tests"}
          </button>
          {error && (
            <p className="error" role="alert">
              {error}
            </p>
          )}
          {tests !== null && (
            <section className="result">
              <h2>Generated tests</h2>
              <pre>{tests}</pre>
            </section>
          )}
          {execution !== null && (
            <section className="result">
              <h2>Test execution</h2>
              <p
                className={
                  execution.timed_out || execution.return_code !== 0
                    ? "execution-status failed"
                    : "execution-status passed"
                }
                role="status"
              >
                {execution.timed_out
                  ? "Test execution timed out."
                  : execution.return_code === 0
                    ? "Tests passed."
                    : "Tests failed."}
              </p>
              <pre>{execution.output}</pre>
            </section>
          )}
        </form>
      </section>
    </main>
  );
}
