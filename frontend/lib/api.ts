import type {
  PastedCodeGenerationRun,
  RepositoryContext,
  RepositoryFixProposalRun,
  RepositoryFixVerificationRun,
  RepositoryGenerationContextPreview,
  RepositoryGenerationRun,
  RepositoryInvestigationRun,
  RepositoryTestRun,
} from "../types/api";

type ApiError = { detail: string };

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type RepositoryTargeting = {
  reference?: string;
  subdirectory?: string;
  targetPath?: string;
};

function repositoryRequestBody(
  repositoryUrl: string,
  targeting: RepositoryTargeting = {},
) {
  return {
    url: repositoryUrl,
    ...(targeting.reference ? { reference: targeting.reference } : {}),
    ...(targeting.subdirectory ? { subdirectory: targeting.subdirectory } : {}),
    ...(targeting.targetPath ? { target_path: targeting.targetPath } : {}),
  };
}

export async function fetchRepositoryContext(
  repositoryUrl: string,
  targeting: RepositoryTargeting = {},
): Promise<RepositoryContext> {
  const response = await fetch(`${apiUrl}/repository/context`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(repositoryRequestBody(repositoryUrl, targeting)),
  });
  const context: RepositoryContext | ApiError = await response.json();

  if (!response.ok || !("metadata" in context)) {
    throw new Error("detail" in context ? context.detail : "The request failed.");
  }

  return context;
}

export async function previewRepositoryGenerationContext(
  repositoryUrl: string,
  targeting: RepositoryTargeting,
): Promise<RepositoryGenerationContextPreview> {
  const response = await fetch(`${apiUrl}/repository/context/preview`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(repositoryRequestBody(repositoryUrl, targeting)),
  });
  const context: RepositoryGenerationContextPreview | ApiError = await response.json();

  if (!response.ok || !("selection" in context)) {
    throw new Error("detail" in context ? context.detail : "The preview request failed.");
  }

  return context;
}

export async function runRepositoryTests(
  repositoryUrl: string,
  targeting: RepositoryTargeting = {},
): Promise<RepositoryTestRun> {
  const response = await fetch(`${apiUrl}/repository/test-run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(repositoryRequestBody(repositoryUrl, targeting)),
  });
  const result: RepositoryTestRun | ApiError = await response.json();

  if (!response.ok || !("execution" in result)) {
    throw new Error("detail" in result ? result.detail : "The test run failed.");
  }

  return result;
}

export async function generateRepositoryTests(
  repositoryUrl: string,
  targeting: RepositoryTargeting = {},
): Promise<RepositoryGenerationRun> {
  const response = await fetch(`${apiUrl}/repository/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(repositoryRequestBody(repositoryUrl, targeting)),
  });
  const result: RepositoryGenerationRun | ApiError = await response.json();

  if (!response.ok || !("generated_execution" in result)) {
    throw new Error("detail" in result ? result.detail : "Test generation failed.");
  }

  return result;
}

export async function investigateRepository(
  repositoryUrl: string,
  targeting: RepositoryTargeting = {},
): Promise<RepositoryInvestigationRun> {
  const response = await fetch(`${apiUrl}/repository/investigate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(repositoryRequestBody(repositoryUrl, targeting)),
  });
  const result: RepositoryInvestigationRun | ApiError = await response.json();

  if (!response.ok || !("investigation" in result)) {
    throw new Error("detail" in result ? result.detail : "Repository investigation failed.");
  }

  return result;
}

export async function proposeRepositoryFix(
  repositoryUrl: string,
  targeting: RepositoryTargeting,
): Promise<RepositoryFixProposalRun> {
  const response = await fetch(`${apiUrl}/repository/fix-proposal`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(repositoryRequestBody(repositoryUrl, targeting)),
  });
  const result: RepositoryFixProposalRun | ApiError = await response.json();

  if (!response.ok || !("proposal" in result)) {
    throw new Error("detail" in result ? result.detail : "Repository fix proposal failed.");
  }

  return result;
}

export async function verifyRepositoryFix(
  repositoryUrl: string,
  proposal: RepositoryFixProposalRun["proposal"],
): Promise<RepositoryFixVerificationRun> {
  const response = await fetch(`${apiUrl}/repository/fix-verify`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      url: repositoryUrl,
      revision: proposal.revision,
      ...(proposal.subdirectory ? { subdirectory: proposal.subdirectory } : {}),
      target_path: proposal.target_path,
      patch: proposal.patch,
      approved: true,
    }),
  });
  const result: RepositoryFixVerificationRun | ApiError = await response.json();

  if (!response.ok || !("applied_in_disposable_workspace" in result)) {
    throw new Error("detail" in result ? result.detail : "Repository fix verification failed.");
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
