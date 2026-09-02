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
      execution: { return_code: 0, output: "passed", timed_out: false, skipped: false },
    });

  try {
    await assert.rejects(
      verifyRepositoryFix("https://github.com/acme/payments", {
        revision: "abc",
        subdirectory: null,
        target_path: "src/example.py",
        summary: "Example",
        patch: "--- a/src/example.py\n+++ b/src/example.py",
        validated: true,
        approval_required: true,
        applied: false,
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
