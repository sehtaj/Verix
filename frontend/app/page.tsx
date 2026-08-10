"use client";

import { FormEvent, useState } from "react";

type TestExecution = {
  return_code: number | null;
  output: string;
  timed_out: boolean;
};

export default function Home() {
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
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/generate`, {
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
      <form className="generator" onSubmit={handleSubmit}>
        <h1>Verix</h1>
        <p>Paste a Python function to generate unit tests.</p>
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
    </main>
  );
}
