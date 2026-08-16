"use client";

import { FormEvent, useState } from "react";

import { generatePastedCodeTests } from "../lib/api";
import type { TestExecution } from "../types/api";

export function PastedCodeGenerator() {
  const [code, setCode] = useState("");
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
  );
}
