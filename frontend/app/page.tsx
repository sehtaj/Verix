"use client";

import { FormEvent, useState } from "react";


export default function Home() {
  const [code, setCode] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsLoading(true);

    try {
      await fetch(`${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code }),
      });
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
      </form>
    </main>
  );
}
