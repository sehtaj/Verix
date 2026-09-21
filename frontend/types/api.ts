export type TestExecution = {
  return_code: number | null;
  output: string;
  timed_out: boolean;
};

export type RepositoryMetadata = {
  name: string;
  owner: string;
  description: string | null;
  language: string | null;
  stars: number;
  url: string;
};

export type RepositoryTree = {
  entries: Array<{ path: string; type: string }>;
  is_truncated: boolean;
};

export type RepositoryTestPlan = {
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

export type RepositoryGenerationSelection = {
  target_path: string | null;
  related_test_paths: string[];
  configuration_paths: string[];
  documentation_paths: string[];
  is_truncated: boolean;
};

export type RepositoryConfigurationFile = {
  path: string;
  content: string;
};

export type RepositoryFileContent = RepositoryConfigurationFile & {
  byte_count: number;
};

export type RepositoryContext = {
  revision: string;
  subdirectory: string | null;
  metadata: RepositoryMetadata;
  tree: RepositoryTree;
  configuration_files: RepositoryConfigurationFile[];
  test_plan: RepositoryTestPlan;
  generation_selection: RepositoryGenerationSelection;
};

export type RepositoryGenerationContextPreview = {
  revision: string;
  subdirectory: string | null;
  selection: RepositoryGenerationSelection;
  source_file: RepositoryFileContent | null;
  test_files: RepositoryFileContent[];
  documentation_files: RepositoryFileContent[];
  configuration_files: RepositoryConfigurationFile[];
  skipped_paths: string[];
  total_bytes: number;
};

export type RepositoryPreparation = {
  file_count: number;
  total_bytes: number;
  skipped_entries: number;
};

export type RepositoryExecution = TestExecution & { skipped: boolean };

type BranchCoverageMeasurement = {
  covered_branches: number;
  total_branches: number;
  percent: number;
};

export type BranchCoverageSummary = {
  target_path: string;
} & (
  | {
      available: true;
      existing: BranchCoverageMeasurement;
      combined: BranchCoverageMeasurement;
      incremental_covered_branches: number;
      untested_branches: number;
      unavailable_reason: null;
    }
  | {
      available: false;
      existing: null;
      combined: null;
      incremental_covered_branches: null;
      untested_branches: null;
      unavailable_reason: string;
    }
);

export type RepositoryTestRun = {
  preparation: RepositoryPreparation;
  installation: RepositoryExecution;
  test_runner: string;
  execution: RepositoryExecution;
};

export type RepositoryGenerationRun = {
  target_path: string;
  generated_tests: string;
  generated_test_report: GeneratedTestReport;
  preparation: RepositoryPreparation;
  installation: RepositoryExecution;
  test_runner: string;
  existing_execution: RepositoryExecution;
  generated_execution: RepositoryExecution;
  branch_coverage: BranchCoverageSummary;
  evidence_summary: EvidenceSummary;
};

export type EvidenceSummary = {
  assessment: "observed_failures" | "incomplete" | "no_observed_failures";
  passed: string[];
  failed: string[];
  assumed: string[];
  untested: string[];
  behavior_sources: Array<{
    kind: "source_code" | "documentation" | "existing_test" | "configuration";
    path: string;
  }>;
  disclaimer: string;
};

export type GeneratedTestReport = {
  model: string;
  sources: Array<{
    kind: "source_code" | "documentation" | "existing_test" | "configuration";
    path: string;
    excerpt: string;
  }>;
  assumptions: string[];
  cases: Array<{
    test_name: string;
    category: "normal" | "boundary" | "invalid_input" | "error_handling";
    strategy: "black_box" | "gray_box";
    expected_behavior: string;
  }>;
};

export type RepositoryInvestigationRun = RepositoryGenerationRun & {
  test_plan: RepositoryTestPlan;
  investigation: {
    outcome:
      | "setup_failed"
      | "no_existing_tests"
      | "existing_tests_timed_out"
      | "existing_tests_failed"
      | "generated_tests_timed_out"
      | "generated_tests_failed"
      | "tests_passed";
    explanation: string;
  };
};

export type RepositoryFixProposalRun = RepositoryInvestigationRun & {
  proposal: {
    revision: string;
    subdirectory: string | null;
    target_path: string;
    summary: string;
    patch: string;
    validated: boolean;
    approval_required: boolean;
    applied: boolean;
  };
};

export type RepositoryFixVerificationRun = {
  revision: string;
  subdirectory: string | null;
  target_path: string;
  approved: true;
  applied_in_disposable_workspace: true;
  github_changed: false;
  test_runner: "pytest" | "tox";
  installation: RepositoryExecution;
  existing_execution: RepositoryExecution;
  exposing_execution: RepositoryExecution;
};
