import assert from "node:assert/strict";
import test from "node:test";

import {
  ApiError,
  fetchRepositoryContext,
  generateRepositoryTests,
  runRepositoryTests,
  verifyRepositoryFix,
} from "./api.ts";

const revision = "a".repeat(40);

function generatedTestReport() {
  return {
    model: "gemini-test",
    sources: [
      {
        kind: "source_code",
        path: "src/example.py",
        excerpt: "def example",
      },
    ],
    assumptions: [],
    cases: [
      {
        test_name: "test_example",
        category: "normal",
        strategy: "black_box",
        expected_behavior: "The example follows its public contract.",
      },
    ],
  };
}

function repositoryContext(overrides = {}) {
  return {
    revision,
    subdirectory: null,
    metadata: {
      name: "project",
      owner: "owner",
      description: null,
      language: "Python",
      stars: 0,
      url: "https://github.com/owner/project",
    },
    tree: {
      entries: [{ path: "src/example.py", type: "blob" }],
      is_truncated: false,
    },
    configuration_files: [],
    test_plan: {
      setup: {
        is_python_project: true,
        project_tool: null,
        test_runner: "pytest",
        configuration_files: [],
      },
      source_paths: ["src/example.py"],
      test_paths: [],
      steps: [],
      is_truncated: false,
    },
    generation_selection: {
      target_path: "src/example.py",
      related_test_paths: [],
      configuration_paths: [],
      documentation_paths: [],
      is_truncated: false,
    },
    ...overrides,
  };
}

function jsonResponse(payload, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

test("rejects incomplete successful API payloads at the network boundary", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => jsonResponse({ metadata: {} });

  try {
    await assert.rejects(
      fetchRepositoryContext("https://github.com/acme/payments"),
      /Unable to fetch repository context/,
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("rejects verification payloads that omit required safety facts", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () =>
    jsonResponse({
      revision: "abc",
      subdirectory: null,
      target_path: "src/example.py",
      approved: true,
      test_runner: "pytest",
      installation: { return_code: 0, output: "", timed_out: false, skipped: true },
      existing_execution: { return_code: 0, output: "passed", timed_out: false, skipped: false },
      exposing_execution: { return_code: 0, output: "passed", timed_out: false, skipped: false },
    });

  try {
    await assert.rejects(
      verifyRepositoryFix("https://github.com/acme/payments", {
        generated_tests: "def test_exposing_behavior():\n    assert True\n",
        proposal: {
          revision: "abc",
          subdirectory: null,
          target_path: "src/example.py",
          summary: "Example",
          patch: "--- a/src/example.py\n+++ b/src/example.py",
          validated: true,
          approval_required: true,
          applied: false,
        },
      }),
      /Unable to verify the approved patch/,
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("surfaces structured FastAPI validation messages", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () =>
    jsonResponse(
      { detail: [{ loc: ["body", "url"], msg: "Not a public GitHub repository" }] },
      422,
    );

  try {
    await assert.rejects(fetchRepositoryContext("https://example.com/repository"), (error) => {
      assert.ok(error instanceof ApiError);
      assert.equal(error.field, "url");
      assert.match(error.message, /url: Not a public GitHub repository/);
      return true;
    });
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("rejects a context whose selected target is not in the verified source paths", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () =>
    jsonResponse(repositoryContext({
      generation_selection: {
        target_path: "src/other.py",
        related_test_paths: [],
        configuration_paths: [],
        documentation_paths: [],
        is_truncated: false,
      },
    }));

  try {
    await assert.rejects(
      fetchRepositoryContext("https://github.com/owner/project"),
      /Unable to fetch repository context/,
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("rejects stale pinned context and mismatched generated targets", async () => {
  const originalFetch = globalThis.fetch;

  try {
    globalThis.fetch = async () => jsonResponse(repositoryContext());
    await assert.rejects(
      fetchRepositoryContext("https://github.com/owner/project", { reference: "b".repeat(40) }),
      /Unable to fetch repository context/,
    );

    globalThis.fetch = async () => jsonResponse({
      target_path: "src/other.py",
      generated_tests: "def test_example():\n    assert True\n",
      generated_test_report: generatedTestReport(),
      preparation: { file_count: 1, total_bytes: 10, skipped_entries: 0 },
      installation: { return_code: 0, output: "", timed_out: false, skipped: true },
      test_runner: "pytest",
      existing_execution: { return_code: 5, output: "", timed_out: false, skipped: false },
      generated_execution: { return_code: 0, output: "1 passed", timed_out: false, skipped: false },
    });
    await assert.rejects(
      generateRepositoryTests("https://github.com/owner/project", { targetPath: "src/example.py" }),
      /Unable to generate focused tests/,
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("rejects generated results without expected-behavior provenance", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => jsonResponse({
    target_path: "src/example.py",
    generated_tests: "def test_example():\n    assert True\n",
    preparation: { file_count: 1, total_bytes: 10, skipped_entries: 0 },
    installation: { return_code: 0, output: "", timed_out: false, skipped: true },
    test_runner: "pytest",
    existing_execution: { return_code: 5, output: "", timed_out: false, skipped: false },
    generated_execution: { return_code: 0, output: "1 passed", timed_out: false, skipped: false },
  });

  try {
    await assert.rejects(
      generateRepositoryTests("https://github.com/owner/project", { targetPath: "src/example.py" }),
      /Unable to generate focused tests/,
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("rejects invalid generated-test classifications", async () => {
  const originalFetch = globalThis.fetch;
  const report = generatedTestReport();
  report.cases[0].category = "performance";
  globalThis.fetch = async () => jsonResponse({
    target_path: "src/example.py",
    generated_tests: "def test_example():\n    assert True\n",
    generated_test_report: report,
    preparation: { file_count: 1, total_bytes: 10, skipped_entries: 0 },
    installation: { return_code: 0, output: "", timed_out: false, skipped: true },
    test_runner: "pytest",
    existing_execution: { return_code: 5, output: "", timed_out: false, skipped: false },
    generated_execution: { return_code: 0, output: "1 passed", timed_out: false, skipped: false },
  });

  try {
    await assert.rejects(
      generateRepositoryTests("https://github.com/owner/project", { targetPath: "src/example.py" }),
      /Unable to generate focused tests/,
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("rejects context that crosses repository or project-folder identity", async () => {
  const originalFetch = globalThis.fetch;

  try {
    globalThis.fetch = async () => jsonResponse(repositoryContext({
      metadata: {
        ...repositoryContext().metadata,
        url: "https://github.com/owner/other-project",
      },
    }));
    await assert.rejects(
      fetchRepositoryContext("https://github.com/owner/project"),
      /Unable to fetch repository context/,
    );

    globalThis.fetch = async () => jsonResponse(repositoryContext({ subdirectory: "packages/other" }));
    await assert.rejects(
      fetchRepositoryContext("https://github.com/owner/project", { subdirectory: "packages/core" }),
      /Unable to fetch repository context/,
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("rejects malformed execution and preparation facts", async () => {
  const originalFetch = globalThis.fetch;
  const baseRun = {
    preparation: { file_count: 1, total_bytes: 10, skipped_entries: 0 },
    installation: { return_code: 0, output: "", timed_out: false, skipped: true },
    test_runner: "pytest",
    execution: { return_code: 0, output: "1 passed", timed_out: false, skipped: false },
  };

  try {
    globalThis.fetch = async () => jsonResponse({
      ...baseRun,
      preparation: { ...baseRun.preparation, file_count: -1 },
    });
    await assert.rejects(
      runRepositoryTests("https://github.com/owner/project"),
      /Unable to run repository tests/,
    );

    globalThis.fetch = async () => jsonResponse({
      ...baseRun,
      execution: { return_code: 0.5, output: "", timed_out: true, skipped: true },
    });
    await assert.rejects(
      runRepositoryTests("https://github.com/owner/project"),
      /Unable to run repository tests/,
    );

    globalThis.fetch = async () => jsonResponse({ ...baseRun, test_runner: "shell" });
    await assert.rejects(
      runRepositoryTests("https://github.com/owner/project"),
      /Unable to run repository tests/,
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("sends the exact displayed exposing test and accepts separate verification evidence", async () => {
  const originalFetch = globalThis.fetch;
  let requestBody;
  const generatedTests = "def test_exposing_behavior():\n    assert add(2, 3) == 5\n";
  globalThis.fetch = async (_url, options) => {
    requestBody = JSON.parse(options.body);
    return jsonResponse({
      revision,
      subdirectory: null,
      target_path: "src/example.py",
      approved: true,
      applied_in_disposable_workspace: true,
      github_changed: false,
      test_runner: "pytest",
      installation: { return_code: 0, output: "installed", timed_out: false, skipped: false },
      existing_execution: { return_code: 0, output: "8 passed", timed_out: false, skipped: false },
      exposing_execution: { return_code: 0, output: "1 passed", timed_out: false, skipped: false },
    });
  };

  try {
    const result = await verifyRepositoryFix("https://github.com/owner/project", {
      generated_tests: generatedTests,
      proposal: {
        revision,
        subdirectory: null,
        target_path: "src/example.py",
        summary: "Correct addition.",
        patch: "--- a/src/example.py\n+++ b/src/example.py",
        validated: true,
        approval_required: true,
        applied: false,
      },
    });

    assert.equal(requestBody.generated_tests, generatedTests);
    assert.equal(requestBody.approved, true);
    assert.equal(result.existing_execution.return_code, 0);
    assert.equal(result.exposing_execution.return_code, 0);
  } finally {
    globalThis.fetch = originalFetch;
  }
});
