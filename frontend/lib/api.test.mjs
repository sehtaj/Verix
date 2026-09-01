import assert from "node:assert/strict";
import test from "node:test";

import { fetchRepositoryContext, verifyRepositoryFix } from "./api.ts";

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
    await assert.rejects(
      fetchRepositoryContext("https://example.com/repository"),
      /url: Not a public GitHub repository/,
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});
