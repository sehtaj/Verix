import assert from "node:assert/strict";
import test from "node:test";

import {
  didInstallationSucceed,
  getActionRecoveryScreen,
  getExecutionLabel,
  getExecutionStatus,
  getFixVerificationStatus,
  getOutcomeLabel,
  getReadyScreen,
  getVerificationRecoveryScreen,
  getWorkflowSteps,
  getWorkflowStepStatusLabel,
} from "./repository-results.ts";

const execution = (overrides = {}) => ({
  return_code: 0,
  output: "",
  timed_out: false,
  skipped: false,
  ...overrides,
});

test("classifies every repository execution state without treating no tests as passed", () => {
  assert.equal(getExecutionStatus(execution()), "passed");
  assert.equal(getExecutionStatus(execution({ return_code: 1 })), "failed");
  assert.equal(getExecutionStatus(execution({ return_code: 5 })), "no_tests");
  assert.equal(getExecutionStatus(execution({ timed_out: true })), "timed_out");
  assert.equal(getExecutionStatus(execution({ skipped: true })), "skipped");
  assert.equal(getExecutionLabel("no_tests"), "No Tests Collected");
  assert.equal(didInstallationSucceed(execution({ skipped: true })), true);
  assert.equal(didInstallationSucceed(execution({ return_code: 1 })), false);
  assert.equal(didInstallationSucceed(execution({ timed_out: true })), false);
});

test("requires the generated exposing test and any existing suite to pass verification", () => {
  const result = {
    existing_execution: execution(),
    exposing_execution: execution(),
  };

  assert.equal(getFixVerificationStatus(result), "passed");
  assert.equal(
    getFixVerificationStatus({
      ...result,
      existing_execution: execution({ return_code: 5 }),
    }),
    "passed",
  );
  assert.equal(
    getFixVerificationStatus({
      ...result,
      existing_execution: execution({ return_code: 1 }),
    }),
    "failed",
  );
  assert.equal(
    getFixVerificationStatus({
      ...result,
      exposing_execution: execution({ return_code: 1 }),
    }),
    "failed",
  );
});

test("maps all seven investigation outcomes to distinct user-facing labels", () => {
  const outcomes = [
    "setup_failed",
    "no_existing_tests",
    "existing_tests_timed_out",
    "existing_tests_failed",
    "generated_tests_timed_out",
    "generated_tests_failed",
    "tests_passed",
  ];
  const labels = outcomes.map((outcome) => getOutcomeLabel(outcome));

  assert.equal(new Set(labels).size, outcomes.length);
  assert.deepEqual(labels, [
    "Setup Failed",
    "No Existing Tests",
    "Existing Tests Timed Out",
    "Existing Tests Failed",
    "Generated Tests Timed Out",
    "Generated Tests Failed",
    "Tests Passed",
  ]);
});

test("derives coherent progress states for every workflow stage", () => {
  assert.deepEqual(
    getWorkflowSteps("new_verification").map((step) => step.status),
    ["active", "upcoming", "upcoming", "upcoming", "upcoming"],
  );
  assert.deepEqual(
    getWorkflowSteps("running_existing_tests").map((step) => step.status),
    ["complete", "running", "upcoming", "upcoming", "upcoming"],
  );
  assert.deepEqual(
    getWorkflowSteps("reviewing_fix").map((step) => step.status),
    ["complete", "complete", "complete", "active", "upcoming"],
  );
  assert.deepEqual(
    getWorkflowSteps("showing_verification_result", {
      verificationStatus: "passed",
      verificationSafetyConfirmed: true,
    }).map((step) => step.status),
    ["complete", "complete", "complete", "complete", "complete"],
  );
  assert.deepEqual(
    getWorkflowSteps("showing_verification_result", {
      verificationStatus: "failed",
      verificationSafetyConfirmed: true,
    }).map((step) => step.status),
    ["complete", "complete", "complete", "complete", "failed"],
  );
});

test("keeps action failures attached to the evidence screen that launched them", () => {
  const contextWithTests = {
    test_plan: { test_paths: ["tests/test_example.py"] },
  };
  const contextWithoutTests = {
    test_plan: { test_paths: [] },
  };

  assert.equal(getReadyScreen(contextWithTests), "ready_existing_tests");
  assert.equal(getReadyScreen(contextWithoutTests), "ready_generate_tests");
  assert.equal(
    getActionRecoveryScreen("showing_test_result", contextWithTests, ["showing_test_result"]),
    "showing_test_result",
  );
  assert.equal(
    getActionRecoveryScreen("generating_tests", contextWithoutTests, ["showing_generation_result"]),
    "ready_generate_tests",
  );
  assert.equal(
    getVerificationRecoveryScreen("showing_verification_result"),
    "showing_verification_result",
  );
  assert.equal(getVerificationRecoveryScreen("reviewing_fix"), "reviewing_fix");
});

test("provides an assistive label for every workflow step state", () => {
  assert.equal(getWorkflowStepStatusLabel("upcoming"), "Upcoming");
  assert.equal(getWorkflowStepStatusLabel("active"), "Current");
  assert.equal(getWorkflowStepStatusLabel("running"), "In Progress");
  assert.equal(getWorkflowStepStatusLabel("complete"), "Completed");
  assert.equal(getWorkflowStepStatusLabel("warning"), "Completed with Warnings");
  assert.equal(getWorkflowStepStatusLabel("failed"), "Failed");
});

test("marks failed and inconclusive run evidence without hiding later workflow progress", () => {
  assert.equal(
    getWorkflowSteps("showing_investigation", { existingStatus: "failed", generatedStatus: "passed" })[1].status,
    "failed",
  );
  assert.equal(
    getWorkflowSteps("showing_investigation", { existingStatus: "no_tests", generatedStatus: "passed" })[1].status,
    "warning",
  );
  assert.equal(
    getWorkflowSteps("showing_investigation", { existingStatus: "passed", generatedStatus: "passed" })[2].status,
    "active",
  );
});
