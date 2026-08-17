import type {
  PastedCodeGenerationRun,
  RepositoryContext,
  RepositoryGenerationRun,
  RepositoryTestRun,
} from "../types/api";

type ApiError = { detail: string };

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function fetchRepositoryContext(
  repositoryUrl: string,
): Promise<RepositoryContext> {
  const response = await fetch(`${apiUrl}/repository/context`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url: repositoryUrl }),
  });
  const context: RepositoryContext | ApiError = await response.json();

  if (!response.ok || !("metadata" in context)) {
    throw new Error("detail" in context ? context.detail : "The request failed.");
  }

  return context;
}

export async function runRepositoryTests(
  repositoryUrl: string,
): Promise<RepositoryTestRun> {
  const response = await fetch(`${apiUrl}/repository/test-run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url: repositoryUrl }),
  });
  const result: RepositoryTestRun | ApiError = await response.json();

  if (!response.ok || !("execution" in result)) {
    throw new Error("detail" in result ? result.detail : "The test run failed.");
  }

  return result;
}

export async function generateRepositoryTests(
  repositoryUrl: string,
): Promise<RepositoryGenerationRun> {
  const response = await fetch(`${apiUrl}/repository/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url: repositoryUrl }),
  });
  const result: RepositoryGenerationRun | ApiError = await response.json();

  if (!response.ok || !("generated_execution" in result)) {
    throw new Error("detail" in result ? result.detail : "Test generation failed.");
  }

  return result;
}

export async function generatePastedCodeTests(
  code: string,
): Promise<PastedCodeGenerationRun> {
  const response = await fetch(`${apiUrl}/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code }),
  });

  if (!response.ok) {
    throw new Error("The request failed.");
  }

  return response.json();
}
