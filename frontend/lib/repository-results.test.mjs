import assert from "node:assert/strict";
import test from "node:test";

import {
  didInstallationSucceed,
  getExecutionLabel,
  getExecutionStatus,
  getOutcomeLabel,
  getWorkflowSteps,
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
