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

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function isPublicGitHubRepositoryUrl(value: string): boolean {
  try {
    const url = new URL(value);
    const pathSegments = url.pathname.split("/").filter(Boolean);

    return (
      url.protocol === "https:" &&
      url.hostname === "github.com" &&
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
      return;
    }

    setIsRepositoryLoading(true);
    setRepositoryError(null);
    setRepository(null);

    try {
      const response = await fetch(`${apiUrl}/repository`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: repositoryUrl }),
      });
      const result: RepositoryMetadata | { detail: string } = await response.json();

      if (!response.ok || !("name" in result)) {
        throw new Error("detail" in result ? result.detail : "The request failed.");
      }

      setRepository(result);
    } catch (error) {
      setRepositoryError(
        error instanceof Error ? error.message : "Unable to fetch repository metadata. Please try again.",
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
