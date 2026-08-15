# Agent Instructions for Verix

This file defines how an AI coding agent should work in this repository. It intentionally contains stable working rules. The current version and current task always belong in `TODO.md`, not here.

## Project purpose

Verix is a Python-first AI software quality engineer. It is being built to understand code, generate tests, execute tests safely, investigate failures, and eventually propose verified fixes with user approval.

Current technologies include FastAPI, Pydantic, Python, Next.js, React, TypeScript, Gemini, Docker, and GitHub's public API. Do not add future infrastructure merely because it appears on the roadmap.

## Required reading

Before changing anything, read these files completely in this order:

1. `AGENTS.md`
2. `PROJECT.md`
3. `ARCHITECTURE.md`
4. `README.md`
5. `TODO.md`

Then inspect the working tree so existing user changes are preserved.

Use the documents as follows:

- `PROJECT.md`: product vision, version goals, roadmap, and principles.
- `ARCHITECTURE.md`: actual system design, API flow, security boundaries, and folder structure.
- `README.md`: actual setup and usage instructions.
- `TODO.md`: the active version, ordered tasks, and single Current Task.

If documents disagree with code, do not silently guess. During development, follow the Current Task and report the mismatch. During an explicitly requested Review Phase, synchronize the documents with the verified implementation.

## Communication with the user

Before implementing a task:

1. Explain in simple language what will be changed.
2. Explain why the change is needed.

After implementing it:

1. Explain what changed using simple wording.
2. Explain every created or modified file.
3. List the verification performed and whether it passed.
4. State any limitation, assumption, or unresolved risk honestly.

Avoid unexplained jargon. When a technical term is necessary, define it briefly. The user is learning the system and should be able to understand the explanation without reading it twice.

## Development Phase workflow

Unless the user explicitly enters a Review Phase or gives different instructions:

1. Implement only the task named under **Current Task** in `TODO.md`.
2. Do not implement later tasks or future-version features.
3. Keep the solution as small as reasonably possible.
4. Test the changed behavior in proportion to its risk.
5. Update `TODO.md` only:
   - mark the completed task;
   - set the next incomplete task as Current Task.
6. Do not update `PROJECT.md`, `ARCHITECTURE.md`, or `README.md` during development.
7. Do not commit or push unless the user explicitly asks.
8. Stop after the Current Task is complete.

If the user explicitly requests several remaining tasks or a complete version, those tasks become the authorized scope. Do not expand beyond that version.

## Review Phase workflow

Enter a Review Phase only when the user explicitly requests it.

During review:

1. Test the complete current version.
2. Check for regressions, obvious bugs, dead code, duplication, and unnecessary complexity.
3. Make only small correctness or maintainability improvements; do not add features from the next version.
4. Synchronize `PROJECT.md`, `ARCHITECTURE.md`, and `README.md` with the verified code.
5. Mark the reviewed version complete in `TODO.md` and prepare the next version's task list and Current Task.
6. Summarize tests, bugs, fixes, documentation changes, limitations, and suggestions.
7. Do not commit or push unless the user explicitly asks.
8. Stop after the review is complete.

The project's Definition of Done is satisfied across both phases: implementation is verified during development, while documentation synchronization and final commits happen during review and its approved handoff.

## Git rules

- Work on the current branch unless the user asks for another branch.
- The user currently prefers `main`; do not create a branch without discussing why it is useful.
- Preserve unrelated or pre-existing changes.
- Never discard changes with destructive Git commands unless the user explicitly requests it.
- Never commit, push, rewrite history, or open a pull request without explicit permission.
- Before making a set of version/review commits, propose the number and logical split, then wait for approval.
- Keep commits small, meaningful, and ordered so each commit has a clear purpose.
- Never commit `.env`, API keys, credentials, temporary workspaces, build output, or dependency directories.

## Architecture and scope rules

- Keep the frontend responsible for interface state and rendering.
- Keep business logic and external-service coordination in the backend.
- Keep API keys on the backend only.
- Never execute submitted, generated, repository, dependency-build, or test code directly on the host.
- Preserve Docker isolation, timeouts, resource limits, archive limits, safe path handling, and temporary-workspace cleanup.
- Do not accept repository-provided shell commands. Commands must be selected and assembled by trusted backend code.
- Treat dependency installation as untrusted code execution even when it is inside Docker.
- Prefer focused context over sending an entire repository to an LLM.
- Keep existing-test results separate from generated-test results so failures can be attributed correctly.
- Support Python well before expanding to additional languages.
- Do not add authentication, databases, Redis, queues, RAG, MCP, LangGraph, GitHub Apps, or deployment infrastructure until a current task clearly requires them.
- Do not refactor into extra layers merely for style. Add structure when current files become genuinely difficult to maintain or test.

## Verification expectations

Use the smallest reliable checks that cover the change. Depending on the affected area, these may include:

- Backend syntax: `python3 -m compileall backend`
- Backend deterministic tests once present
- Frontend production and TypeScript validation: `npm run build` from `frontend/`
- Docker runner image and focused isolated execution checks
- API contract checks with FastAPI's test client
- Browser verification for user-visible workflows
- `git diff --check` before handoff or commit

Do not claim a check passed unless it was actually run. If Docker, network access, an API key, or another required service is unavailable, report exactly what could and could not be verified.

## Security and privacy

- Never print, expose, copy, or commit values from `backend/.env`.
- Do not send repository code, secrets, or user data to additional services unless the current feature explicitly requires it and the user understands the flow.
- Use safe, bounded parsing for untrusted repository data.
- Do not weaken security controls merely to make a test pass.
- Clearly distinguish local-development isolation from production-grade multi-tenant security.

## Decision rule

When uncertain, choose the smallest change that completes the Current Task without making a future task harder. Ask the user before making a product decision, adding a dependency, changing architecture, weakening a safety boundary, or expanding scope.
