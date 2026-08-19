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

export type RepositoryContext = {
  metadata: RepositoryMetadata;
  tree: RepositoryTree;
  test_plan: RepositoryTestPlan;
};

export type RepositoryPreparation = {
  file_count: number;
  total_bytes: number;
  skipped_entries: number;
};

export type RepositoryExecution = TestExecution & { skipped: boolean };

export type RepositoryTestRun = {
  preparation: RepositoryPreparation;
  installation: RepositoryExecution;
  test_runner: string;
  execution: RepositoryExecution;
};

export type RepositoryGenerationRun = {
  target_path: string;
  generated_tests: string;
  preparation: RepositoryPreparation;
  installation: RepositoryExecution;
  test_runner: string;
  existing_execution: RepositoryExecution;
  generated_execution: RepositoryExecution;
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

export type PastedCodeGenerationRun = {
  tests: string;
  execution: TestExecution;
};
