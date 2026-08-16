"use client";

import { FormEvent, useState } from "react";

import {
  RepositoryGenerationResult,
  RepositoryTestRunResult,
} from "../components/repository-execution-results";
import {
  RepositorySummary,
  RepositoryTestPlanPanel,
  RepositoryTreeView,
} from "../components/repository-inspection";
import { generatePastedCodeTests } from "../lib/api";
import { useRepositoryWorkflow } from "../hooks/use-repository-workflow";
import type { TestExecution } from "../types/api";

export default function Home() {
  const [code, setCode] = useState("");
  const {
    repositoryUrl,
    setRepositoryUrl,
    repository,
    repositoryTree,
    repositoryTestPlan,
    isRepositoryLoading,
    repositoryError,
    repositoryTestRun,
    isRepositoryTestRunning,
    repositoryTestError,
    repositoryGenerationRun,
    isRepositoryGenerationRunning,
    repositoryGenerationError,
    handleRepositorySubmit,
    handleRepositoryTestRun,
    handleRepositoryGeneration,
  } = useRepositoryWorkflow();
  const [isLoading, setIsLoading] = useState(false);
  const [tests, setTests] = useState<string | null>(null);
  const [execution, setExecution] = useState<TestExecution | null>(null);
  const [error, setError] = useState<string | null>(null);

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
          <RepositorySummary repository={repository} />
        )}
        {repositoryTree !== null && (
          <RepositoryTreeView tree={repositoryTree} />
        )}
        {repositoryTestPlan !== null && (
          <RepositoryTestPlanPanel
            plan={repositoryTestPlan}
            isRepositoryLoading={isRepositoryLoading}
            isRepositoryTestRunning={isRepositoryTestRunning}
            isRepositoryGenerationRunning={isRepositoryGenerationRunning}
            repositoryTestError={repositoryTestError}
            repositoryGenerationError={repositoryGenerationError}
            onRunRepositoryTests={handleRepositoryTestRun}
            onGenerateRepositoryTests={handleRepositoryGeneration}
          />
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
