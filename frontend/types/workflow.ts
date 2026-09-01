export type WorkflowScreen =
  | "new_verification"
  | "loading_context"
  | "ready_existing_tests"
  | "ready_generate_tests"
  | "running_existing_tests"
  | "showing_test_result"
  | "generating_tests"
  | "showing_generation_result"
  | "investigating"
  | "showing_investigation"
  | "proposing_fix"
  | "reviewing_fix"
  | "verifying_fix"
  | "showing_verification_result";

export type WorkflowStepStatus =
  | "upcoming"
  | "active"
  | "running"
  | "complete"
  | "failed";

export type WorkflowStep = {
  id: "context" | "run" | "investigate" | "review" | "verify";
  label: string;
  status: WorkflowStepStatus;
};
