"use client";

import { FormEvent, useState } from "react";

type TestExecution = {
  return_code: number | null;
  output: string;
  timed_out: boolean;
};

type RepositoryMetadata = {
  name: string;
  owner: string;
  description: string | null;
  language: string | null;
  stars: number;
  url: string;
};

type RepositoryTree = {
  entries: Array<{ path: string; type: string }>;
  is_truncated: boolean;
};

type RepositoryTestPlan = {
  setup: {
    is_python_project: boolean;
    project_tool: string | null;
    test_runner: string | null;
    configuration_files: string[];
  };
  source_paths: string[];
  test_paths: string[];
  steps: Array<{
    action: string;
    description: string;
    command: string | null;
  }>;
  is_truncated: boolean;
};

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

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
      return;
    }

    setIsRepositoryLoading(true);
    setRepositoryError(null);
    setRepository(null);
    setRepositoryTree(null);
    setRepositoryTestPlan(null);

    try {
      const metadataResponse = await fetch(`${apiUrl}/repository`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: repositoryUrl }),
      });
      const metadata: RepositoryMetadata | { detail: string } = await metadataResponse.json();

      if (!metadataResponse.ok || !("name" in metadata)) {
        throw new Error("detail" in metadata ? metadata.detail : "The request failed.");
      }

      const [treeResponse, testPlanResponse] = await Promise.all([
        fetch(`${apiUrl}/repository/tree`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ url: repositoryUrl }),
        }),
        fetch(`${apiUrl}/repository/test-plan`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ url: repositoryUrl }),
        }),
      ]);
      const [tree, testPlan]: [
        RepositoryTree | { detail: string },
        RepositoryTestPlan | { detail: string },
      ] = await Promise.all([treeResponse.json(), testPlanResponse.json()]);

      if (!treeResponse.ok || !("entries" in tree)) {
        throw new Error("detail" in tree ? tree.detail : "The request failed.");
      }
      if (!testPlanResponse.ok || !("steps" in testPlan)) {
        throw new Error("detail" in testPlan ? testPlan.detail : "The request failed.");
      }

      setRepository(metadata);
      setRepositoryTree(tree);
      setRepositoryTestPlan(testPlan);
    } catch (error) {
      setRepositoryError(
        error instanceof Error ? error.message : "Unable to fetch repository details. Please try again.",
      );
    } finally {
      setIsRepositoryLoading(false);
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
      const response = await fetch(`${apiUrl}/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code }),
      });

      if (!response.ok) {
        throw new Error("The request failed.");
      }

      const result: { tests: string; execution: TestExecution } = await response.json();
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
            disabled={isRepositoryLoading}
            onChange={(event) => setRepositoryUrl(event.target.value)}
          />
          <p className="field-hint">Use an HTTPS URL for a public repository.</p>
          <button disabled={isRepositoryLoading} type="submit">
            {isRepositoryLoading ? "Fetching..." : "Fetch repository"}
          </button>
          {repositoryError && <p className="error">{repositoryError}</p>}
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
          </section>
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
          {error && <p className="error">{error}</p>}
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
