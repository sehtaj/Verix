import type { RepositoryExecution, RepositoryInvestigationRun } from "@/types/api";
import type {
  WorkflowScreen,
  WorkflowStep,
  WorkflowStepStatus,
} from "@/types/workflow";

export type ExecutionStatus =
  | "passed"
  | "failed"
  | "timed_out"
  | "skipped"
  | "no_tests";

export type WorkflowStepEvidence = {
  existingStatus?: ExecutionStatus;
  generatedStatus?: ExecutionStatus;
  investigationOutcome?: RepositoryInvestigationRun["investigation"]["outcome"];
  verificationStatus?: ExecutionStatus;
  verificationSafetyConfirmed?: boolean;
};

export function getExecutionStatus(execution: RepositoryExecution): ExecutionStatus {
  if (execution.skipped) return "skipped";
  if (execution.timed_out) return "timed_out";
  if (execution.return_code === 5) return "no_tests";
  if (execution.return_code === 0) return "passed";
  return "failed";
}

export function getExecutionLabel(status: ExecutionStatus): string {
  return {
    passed: "Passed",
    failed: "Failed",
    timed_out: "Timed Out",
    skipped: "Skipped",
    no_tests: "No Tests Collected",
  }[status];
}

export function didInstallationSucceed(execution: RepositoryExecution): boolean {
  return !execution.timed_out && execution.return_code === 0;
}

export function getOutcomeLabel(
  outcome: RepositoryInvestigationRun["investigation"]["outcome"],
): string {
  return {
    setup_failed: "Setup Failed",
    no_existing_tests: "No Existing Tests",
    existing_tests_timed_out: "Existing Tests Timed Out",
    existing_tests_failed: "Existing Tests Failed",
    generated_tests_timed_out: "Generated Tests Timed Out",
    generated_tests_failed: "Generated Tests Failed",
    tests_passed: "Tests Passed",
  }[outcome];
}

function statusForIndex(
  index: number,
  activeIndex: number,
  running: boolean,
  failedIndex: number | null,
): WorkflowStepStatus {
  if (failedIndex === index) return "failed";
  if (index < activeIndex) return "complete";
  if (index === activeIndex) return running ? "running" : "active";
  return "upcoming";
}

export function getWorkflowSteps(
  screen: WorkflowScreen,
  evidence: WorkflowStepEvidence = {},
): WorkflowStep[] {
  let activeIndex = 0;
  let running = false;
  let failedIndex: number | null = null;

  if (screen === "loading_context") running = true;
  if (screen === "ready_existing_tests" || screen === "ready_generate_tests") {
    activeIndex = 1;
  }
  if (screen === "running_existing_tests" || screen === "generating_tests") {
    activeIndex = 1;
    running = true;
  }
  if (screen === "showing_test_result" || screen === "showing_generation_result") {
    activeIndex = 2;
  }
  if (screen === "showing_test_result" && evidence.existingStatus === "passed") {
    activeIndex = 1;
  }
  if (
    screen === "showing_generation_result" &&
    evidence.generatedStatus === "passed" &&
    ["passed", "no_tests", "skipped"].includes(evidence.existingStatus ?? "skipped")
  ) {
    activeIndex = 1;
  }
  if (screen === "investigating") {
    activeIndex = 2;
    running = true;
  }
  if (screen === "showing_investigation") activeIndex = 2;
  if (screen === "proposing_fix") {
    activeIndex = 3;
    running = true;
  }
  if (screen === "reviewing_fix") activeIndex = 3;
  if (screen === "verifying_fix") {
    activeIndex = 4;
    running = true;
  }
  if (screen === "showing_verification_result") {
    if (evidence.verificationStatus === "passed" && evidence.verificationSafetyConfirmed) {
      activeIndex = 5;
    } else if (evidence.verificationStatus) {
      activeIndex = 4;
      failedIndex = 4;
    } else {
      activeIndex = 4;
    }
  }

  const definitions: Array<Pick<WorkflowStep, "id" | "label">> = [
    { id: "context", label: "Context" },
    { id: "run", label: "Run Tests" },
    { id: "investigate", label: "Investigate" },
    { id: "review", label: "Review Fix" },
    { id: "verify", label: "Verify" },
  ];

  return definitions.map((definition, index) => ({
    ...definition,
    status: statusForIndex(index, activeIndex, running, failedIndex),
  }));
}
