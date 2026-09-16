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

const commitShaPattern = /^[0-9a-f]{40}$/i;

export type ApiField = "url" | "reference" | "subdirectory" | "target_path";

export class ApiError extends Error {
  field: ApiField | null;

  constructor(message: string, field: ApiField | null = null) {
    super(message);
    this.name = "ApiError";
    this.field = field;
  }
}

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

function describeApiDetail(detail: unknown): { message: string; field: ApiField | null } | null {
  if (typeof detail === "string") return { message: detail, field: null };
  if (!Array.isArray(detail)) return null;

  const details = detail
    .map((item) => {
      if (typeof item !== "object" || item === null || !("msg" in item)) return null;
      const message = String(item.msg);
      const locationParts: string[] =
        "loc" in item && Array.isArray(item.loc)
          ? item.loc.filter((part: unknown) => part !== "body").map(String)
          : [];
      const field = locationParts.find((part: string): part is ApiField =>
        ["url", "reference", "subdirectory", "target_path"].includes(part),
      ) ?? null;
      const location = locationParts.join(" → ");
      return { message: location ? `${location}: ${message}` : message, field };
    })
    .filter((item): item is { message: string; field: ApiField | null } => item !== null);

  if (details.length === 0) return null;
  const fields = new Set(details.map((item) => item.field).filter(Boolean));
  return {
    message: details.map((item) => item.message).join(". "),
    field: fields.size === 1 ? ([...fields][0] ?? null) : null,
  };
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
    throw new ApiError("Unable to reach the Verix API. Confirm that the backend is running.");
  }

  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    throw new ApiError(response.ok ? fallbackError : `The Verix API returned HTTP ${response.status}.`);
  }

  if (!response.ok) {
    const detail =
      typeof payload === "object" && payload !== null && "detail" in payload
        ? describeApiDetail(payload.detail)
        : null;
    throw new ApiError(detail?.message ?? fallbackError, detail?.field ?? null);
  }

  if (!isExpectedResponse(payload)) throw new ApiError(fallbackError);
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

function isNonEmptyString(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function isCommitSha(value: unknown): value is string {
  return typeof value === "string" && commitShaPattern.test(value);
}

function isNonNegativeInteger(value: unknown): value is number {
  return Number.isInteger(value) && typeof value === "number" && value >= 0;
}

function isReturnCode(value: unknown): value is number | null {
  return value === null || (typeof value === "number" && Number.isInteger(value));
}

function isTestRunner(value: unknown): value is "pytest" | "tox" {
  return value === "pytest" || value === "tox";
}

function repositoryIdentity(value: string): string | null {
  try {
    const parsed = new URL(value);
    if (parsed.protocol !== "https:" || parsed.hostname.toLowerCase() !== "github.com") return null;
    const parts = parsed.pathname.replace(/\/+$/, "").split("/").filter(Boolean);
    if (parts.length !== 2) return null;
    return `${parts[0].toLowerCase()}/${parts[1].replace(/\.git$/i, "").toLowerCase()}`;
  } catch {
    return null;
  }
}

function matchesRepositoryUrl(actual: string, requested: string): boolean {
  const actualIdentity = repositoryIdentity(actual);
  return actualIdentity !== null && actualIdentity === repositoryIdentity(requested);
}

function matchesSubdirectory(actual: string | null, requested?: string): boolean {
  return actual === (requested ?? null);
}

function matchesPinnedReference(revision: string, reference?: string): boolean {
  return !reference || !commitShaPattern.test(reference) || revision.toLowerCase() === reference.toLowerCase();
}

function isExecution(value: unknown): value is RepositoryExecution {
  return (
    isRecord(value) &&
    isReturnCode(value.return_code) &&
    typeof value.output === "string" &&
    typeof value.timed_out === "boolean" &&
    typeof value.skipped === "boolean" &&
    !(value.skipped && value.timed_out)
  );
}

function isPreparation(value: unknown): value is RepositoryPreparation {
  return (
    isRecord(value) &&
    isNonNegativeInteger(value.file_count) &&
    isNonNegativeInteger(value.total_bytes) &&
    isNonNegativeInteger(value.skipped_entries)
  );
}

function isConfigurationFile(value: unknown): value is { path: string; content: string } {
  return isRecord(value) && typeof value.path === "string" && typeof value.content === "string";
}

function isFileContent(value: unknown): value is { path: string; content: string; byte_count: number } {
  if (!isRecord(value) || !isConfigurationFile(value)) return false;
  return isNonNegativeInteger((value as unknown as Record<string, unknown>).byte_count);
}

function isSelection(value: unknown): value is RepositoryContext["generation_selection"] {
  return (
    isRecord(value) &&
    isNullableString(value.target_path) &&
    isStringArray(value.related_test_paths) &&
    isStringArray(value.configuration_paths) &&
    isStringArray(value.documentation_paths) &&
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
  const hasExpectedShape = (
    isCommitSha(value.revision) &&
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
  if (!hasExpectedShape) return false;

  const context = value as unknown as RepositoryContext;
  const targetPath = context.generation_selection.target_path;
  return targetPath === null || context.test_plan.source_paths.includes(targetPath);
}

function isContextPreview(value: unknown): value is RepositoryGenerationContextPreview {
  const hasExpectedShape = (
    isRecord(value) &&
    isCommitSha(value.revision) &&
    isNullableString(value.subdirectory) &&
    isSelection(value.selection) &&
    (value.source_file === null || isFileContent(value.source_file)) &&
    Array.isArray(value.test_files) &&
    value.test_files.every(isFileContent) &&
    Array.isArray(value.documentation_files) &&
    value.documentation_files.every(isFileContent) &&
    Array.isArray(value.configuration_files) &&
    value.configuration_files.every(isConfigurationFile) &&
    isStringArray(value.skipped_paths) &&
    typeof value.total_bytes === "number"
  );
  if (!hasExpectedShape) return false;

  const preview = value as unknown as RepositoryGenerationContextPreview;
  return (
    preview.selection.target_path !== null &&
    preview.source_file !== null &&
    preview.selection.target_path === preview.source_file.path &&
    preview.test_files.every((file) => preview.selection.related_test_paths.includes(file.path)) &&
    preview.documentation_files.every((file) => preview.selection.documentation_paths.includes(file.path)) &&
    preview.configuration_files.every((file) => preview.selection.configuration_paths.includes(file.path))
  );
}

function isTestRun(value: unknown): value is RepositoryTestRun {
  return (
    isRecord(value) &&
    isPreparation(value.preparation) &&
    isExecution(value.installation) &&
    isTestRunner(value.test_runner) &&
    isExecution(value.execution)
  );
}

function isGenerationRun(value: unknown): value is RepositoryGenerationRun {
  return (
    isRecord(value) &&
    isNonEmptyString(value.target_path) &&
    isNonEmptyString(value.generated_tests) &&
    isGeneratedTestReport(value.generated_test_report) &&
    isPreparation(value.preparation) &&
    isExecution(value.installation) &&
    isTestRunner(value.test_runner) &&
    isExecution(value.existing_execution) &&
    isExecution(value.generated_execution)
  );
}

const behaviorSourceKinds = new Set(["source_code", "documentation", "existing_test", "configuration"]);
const testCaseCategories = new Set(["normal", "boundary", "invalid_input", "error_handling"]);
const testDesignStrategies = new Set(["black_box", "gray_box"]);

function isGeneratedTestReport(value: unknown): boolean {
  return (
    isRecord(value) &&
    isNonEmptyString(value.model) &&
    isStringArray(value.assumptions) &&
    Array.isArray(value.sources) &&
    value.sources.length > 0 &&
    value.sources.every((source) =>
      isRecord(source) &&
      typeof source.kind === "string" && behaviorSourceKinds.has(source.kind) &&
      isNonEmptyString(source.path) &&
      isNonEmptyString(source.excerpt),
    ) &&
    Array.isArray(value.cases) &&
    value.cases.length > 0 &&
    value.cases.every((testCase) =>
      isRecord(testCase) &&
      isNonEmptyString(testCase.test_name) &&
      typeof testCase.category === "string" && testCaseCategories.has(testCase.category) &&
      typeof testCase.strategy === "string" && testDesignStrategies.has(testCase.strategy) &&
      isNonEmptyString(testCase.expected_behavior),
    )
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
    isCommitSha(proposal.revision) &&
    isNullableString(proposal.subdirectory) &&
    isNonEmptyString(proposal.target_path) &&
    isNonEmptyString(proposal.summary) &&
    isNonEmptyString(proposal.patch) &&
    proposal.validated === true &&
    proposal.approval_required === true &&
    proposal.applied === false &&
    proposal.target_path === value.target_path
  );
}

function isFixVerificationRun(value: unknown): value is RepositoryFixVerificationRun {
  return (
    isRecord(value) &&
    isCommitSha(value.revision) &&
    isNullableString(value.subdirectory) &&
    isNonEmptyString(value.target_path) &&
    value.approved === true &&
    value.applied_in_disposable_workspace === true &&
    value.github_changed === false &&
    (value.test_runner === "pytest" || value.test_runner === "tox") &&
    isExecution(value.installation) &&
    isExecution(value.existing_execution) &&
    isExecution(value.exposing_execution)
  );
}

export function fetchRepositoryContext(
  repositoryUrl: string,
  targeting: RepositoryTargeting = {},
): Promise<RepositoryContext> {
  return postJson(
    "/repository/context",
    repositoryRequestBody(repositoryUrl, targeting),
    (payload): payload is RepositoryContext =>
      isRepositoryContext(payload) &&
      matchesRepositoryUrl(payload.metadata.url, repositoryUrl) &&
      matchesSubdirectory(payload.subdirectory, targeting.subdirectory) &&
      matchesPinnedReference(payload.revision, targeting.reference) &&
      (!targeting.targetPath || payload.generation_selection.target_path === targeting.targetPath),
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
    (payload): payload is RepositoryGenerationContextPreview =>
      isContextPreview(payload) &&
      matchesSubdirectory(payload.subdirectory, targeting.subdirectory) &&
      matchesPinnedReference(payload.revision, targeting.reference) &&
      payload.selection.target_path === targeting.targetPath,
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
    (payload): payload is RepositoryGenerationRun =>
      isGenerationRun(payload) &&
      (!targeting.targetPath || payload.target_path === targeting.targetPath),
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
    (payload): payload is RepositoryInvestigationRun =>
      isInvestigationRun(payload) &&
      (!targeting.targetPath || payload.target_path === targeting.targetPath),
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
    (payload): payload is RepositoryFixProposalRun =>
      isFixProposalRun(payload) &&
      (!targeting.targetPath || payload.target_path === targeting.targetPath) &&
      matchesSubdirectory(payload.proposal.subdirectory, targeting.subdirectory) &&
      matchesPinnedReference(payload.proposal.revision, targeting.reference),
    "Unable to propose a source fix.",
  );
}

export function verifyRepositoryFix(
  repositoryUrl: string,
  proposalRun: RepositoryFixProposalRun,
): Promise<RepositoryFixVerificationRun> {
  const { proposal } = proposalRun;
  return postJson(
    "/repository/fix-verify",
    {
      url: repositoryUrl,
      revision: proposal.revision,
      ...(proposal.subdirectory ? { subdirectory: proposal.subdirectory } : {}),
      target_path: proposal.target_path,
      patch: proposal.patch,
      generated_tests: proposalRun.generated_tests,
      approved: true,
    },
    (payload): payload is RepositoryFixVerificationRun =>
      isFixVerificationRun(payload) &&
      payload.revision.toLowerCase() === proposal.revision.toLowerCase() &&
      payload.target_path === proposal.target_path &&
      payload.subdirectory === proposal.subdirectory,
    "Unable to verify the approved patch.",
  );
}
