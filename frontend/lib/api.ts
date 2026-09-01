import type {
  RepositoryContext,
  RepositoryExecution,
  RepositoryFixProposalRun,
  RepositoryFixVerificationRun,
  RepositoryGenerationContextPreview,
  RepositoryGenerationRun,
  RepositoryInvestigationRun,
  RepositoryPreparation,
  RepositoryTestRun,
} from "@/types/api";

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

function describeApiDetail(detail: unknown): string | null {
  if (typeof detail === "string") return detail;
  if (!Array.isArray(detail)) return null;

  const messages = detail
    .map((item) => {
      if (typeof item !== "object" || item === null || !("msg" in item)) return null;
      const message = String(item.msg);
      const location =
        "loc" in item && Array.isArray(item.loc)
          ? item.loc.filter((part: unknown) => part !== "body").join(" → ")
          : "";
      return location ? `${location}: ${message}` : message;
    })
    .filter((message): message is string => message !== null);

  return messages.length > 0 ? messages.join(". ") : null;
}

async function postJson<T>(
  path: string,
  body: object,
  isExpectedResponse: (payload: unknown) => payload is T,
  fallbackError: string,
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${apiUrl}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch {
    throw new Error("Unable to reach the Verix API. Confirm that the backend is running.");
  }

  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    throw new Error(response.ok ? fallbackError : `The Verix API returned HTTP ${response.status}.`);
  }

  if (!response.ok) {
    const detail =
      typeof payload === "object" && payload !== null && "detail" in payload
        ? describeApiDetail(payload.detail)
        : null;
    throw new Error(detail ?? fallbackError);
  }

  if (!isExpectedResponse(payload)) throw new Error(fallbackError);
  return payload;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isNullableString(value: unknown): value is string | null {
  return typeof value === "string" || value === null;
}

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === "string");
}

function isExecution(value: unknown): value is RepositoryExecution {
  return (
    isRecord(value) &&
    (typeof value.return_code === "number" || value.return_code === null) &&
    typeof value.output === "string" &&
    typeof value.timed_out === "boolean" &&
    typeof value.skipped === "boolean"
  );
}

function isPreparation(value: unknown): value is RepositoryPreparation {
  return (
    isRecord(value) &&
    typeof value.file_count === "number" &&
    typeof value.total_bytes === "number" &&
    typeof value.skipped_entries === "number"
  );
}

function isConfigurationFile(value: unknown): value is { path: string; content: string } {
  return isRecord(value) && typeof value.path === "string" && typeof value.content === "string";
}

function isFileContent(value: unknown): value is { path: string; content: string; byte_count: number } {
  if (!isRecord(value) || !isConfigurationFile(value)) return false;
  return typeof (value as unknown as Record<string, unknown>).byte_count === "number";
}

function isSelection(value: unknown): value is RepositoryContext["generation_selection"] {
  return (
    isRecord(value) &&
    isNullableString(value.target_path) &&
    isStringArray(value.related_test_paths) &&
    isStringArray(value.configuration_paths) &&
    typeof value.is_truncated === "boolean"
  );
}

function isTestPlan(value: unknown): value is RepositoryContext["test_plan"] {
  if (!isRecord(value) || !isRecord(value.setup) || !Array.isArray(value.steps)) return false;
  return (
    typeof value.setup.is_python_project === "boolean" &&
    isNullableString(value.setup.project_tool) &&
    isNullableString(value.setup.test_runner) &&
    isStringArray(value.setup.configuration_files) &&
    isStringArray(value.source_paths) &&
    isStringArray(value.test_paths) &&
    value.steps.every(
      (step) =>
        isRecord(step) &&
        typeof step.action === "string" &&
        typeof step.description === "string" &&
        isNullableString(step.command),
    ) &&
    typeof value.is_truncated === "boolean"
  );
}

function isRepositoryContext(value: unknown): value is RepositoryContext {
  if (!isRecord(value) || !isRecord(value.metadata) || !isRecord(value.tree)) return false;
  return (
    typeof value.revision === "string" &&
    isNullableString(value.subdirectory) &&
    typeof value.metadata.name === "string" &&
    typeof value.metadata.owner === "string" &&
    isNullableString(value.metadata.description) &&
    isNullableString(value.metadata.language) &&
    typeof value.metadata.stars === "number" &&
    typeof value.metadata.url === "string" &&
    Array.isArray(value.tree.entries) &&
    value.tree.entries.every(
      (entry) => isRecord(entry) && typeof entry.path === "string" && typeof entry.type === "string",
    ) &&
    typeof value.tree.is_truncated === "boolean" &&
    Array.isArray(value.configuration_files) &&
    value.configuration_files.every(isConfigurationFile) &&
    isTestPlan(value.test_plan) &&
    isSelection(value.generation_selection)
  );
}

function isContextPreview(value: unknown): value is RepositoryGenerationContextPreview {
  return (
    isRecord(value) &&
    typeof value.revision === "string" &&
    isNullableString(value.subdirectory) &&
    isSelection(value.selection) &&
    (value.source_file === null || isFileContent(value.source_file)) &&
    Array.isArray(value.test_files) &&
    value.test_files.every(isFileContent) &&
    Array.isArray(value.configuration_files) &&
    value.configuration_files.every(isConfigurationFile) &&
    isStringArray(value.skipped_paths) &&
    typeof value.total_bytes === "number"
  );
}

function isTestRun(value: unknown): value is RepositoryTestRun {
  return (
    isRecord(value) &&
    isPreparation(value.preparation) &&
    isExecution(value.installation) &&
    typeof value.test_runner === "string" &&
    isExecution(value.execution)
  );
}

function isGenerationRun(value: unknown): value is RepositoryGenerationRun {
  return (
    isRecord(value) &&
    typeof value.target_path === "string" &&
    typeof value.generated_tests === "string" &&
    isPreparation(value.preparation) &&
    isExecution(value.installation) &&
    typeof value.test_runner === "string" &&
    isExecution(value.existing_execution) &&
    isExecution(value.generated_execution)
  );
}

const investigationOutcomes = new Set([
  "setup_failed",
  "no_existing_tests",
  "existing_tests_timed_out",
  "existing_tests_failed",
  "generated_tests_timed_out",
  "generated_tests_failed",
  "tests_passed",
]);

function isInvestigationRun(value: unknown): value is RepositoryInvestigationRun {
  if (!isRecord(value) || !isGenerationRun(value)) return false;
  const record = value as unknown as Record<string, unknown>;
  return (
    isTestPlan(record.test_plan) &&
    isRecord(record.investigation) &&
    typeof record.investigation.outcome === "string" &&
    investigationOutcomes.has(record.investigation.outcome) &&
    typeof record.investigation.explanation === "string"
  );
}

function isFixProposalRun(value: unknown): value is RepositoryFixProposalRun {
  if (!isRecord(value) || !isInvestigationRun(value)) return false;
  const proposal = (value as unknown as Record<string, unknown>).proposal;
  return (
    isRecord(proposal) &&
    typeof proposal.revision === "string" &&
    isNullableString(proposal.subdirectory) &&
    typeof proposal.target_path === "string" &&
    typeof proposal.summary === "string" &&
    typeof proposal.patch === "string" &&
    typeof proposal.validated === "boolean" &&
    typeof proposal.approval_required === "boolean" &&
    typeof proposal.applied === "boolean"
  );
}

function isFixVerificationRun(value: unknown): value is RepositoryFixVerificationRun {
  return (
    isRecord(value) &&
    typeof value.revision === "string" &&
    isNullableString(value.subdirectory) &&
    typeof value.target_path === "string" &&
    value.approved === true &&
    typeof value.applied_in_disposable_workspace === "boolean" &&
    typeof value.github_changed === "boolean" &&
    (value.test_runner === "pytest" || value.test_runner === "tox") &&
    isExecution(value.installation) &&
    isExecution(value.execution)
  );
}

export function fetchRepositoryContext(
  repositoryUrl: string,
  targeting: RepositoryTargeting = {},
): Promise<RepositoryContext> {
  return postJson(
    "/repository/context",
    repositoryRequestBody(repositoryUrl, targeting),
    isRepositoryContext,
    "Unable to fetch repository context.",
  );
}

export function previewRepositoryGenerationContext(
  repositoryUrl: string,
  targeting: RepositoryTargeting,
): Promise<RepositoryGenerationContextPreview> {
  return postJson(
    "/repository/context/preview",
    repositoryRequestBody(repositoryUrl, targeting),
    isContextPreview,
    "Unable to preview the selected context.",
  );
}

export function runRepositoryTests(
  repositoryUrl: string,
  targeting: RepositoryTargeting = {},
): Promise<RepositoryTestRun> {
  return postJson(
    "/repository/test-run",
    repositoryRequestBody(repositoryUrl, targeting),
    isTestRun,
    "Unable to run repository tests.",
  );
}

export function generateRepositoryTests(
  repositoryUrl: string,
  targeting: RepositoryTargeting = {},
): Promise<RepositoryGenerationRun> {
  return postJson(
    "/repository/generate",
    repositoryRequestBody(repositoryUrl, targeting),
    isGenerationRun,
    "Unable to generate focused tests.",
  );
}

export function investigateRepository(
  repositoryUrl: string,
  targeting: RepositoryTargeting = {},
): Promise<RepositoryInvestigationRun> {
  return postJson(
    "/repository/investigate",
    repositoryRequestBody(repositoryUrl, targeting),
    isInvestigationRun,
    "Unable to investigate the repository.",
  );
}

export function proposeRepositoryFix(
  repositoryUrl: string,
  targeting: RepositoryTargeting,
): Promise<RepositoryFixProposalRun> {
  return postJson(
    "/repository/fix-proposal",
    repositoryRequestBody(repositoryUrl, targeting),
    isFixProposalRun,
    "Unable to propose a source fix.",
  );
}

export function verifyRepositoryFix(
  repositoryUrl: string,
  proposal: RepositoryFixProposalRun["proposal"],
): Promise<RepositoryFixVerificationRun> {
  return postJson(
    "/repository/fix-verify",
    {
      url: repositoryUrl,
      revision: proposal.revision,
      ...(proposal.subdirectory ? { subdirectory: proposal.subdirectory } : {}),
      target_path: proposal.target_path,
      patch: proposal.patch,
      approved: true,
    },
    isFixVerificationRun,
    "Unable to verify the approved patch.",
  );
}
