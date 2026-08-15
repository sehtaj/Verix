# Verix

> An AI Software Quality Engineer.

---

# Vision

Verix is an autonomous software quality engineer that helps developers verify AI-generated and human-written code before it reaches production.

Instead of only generating code, Verix focuses on proving correctness by generating tests, executing them safely, identifying failures, explaining bugs, and eventually suggesting verified fixes.

---

# Mission

Developers increasingly rely on AI coding assistants.

Writing code is becoming easier.

Trusting that code is becoming harder.

Verix exists to bridge that gap.

Our goal is to increase confidence in software by automatically verifying correctness before code is merged or deployed.

---

# Problem Statement

Current AI coding assistants can generate code quickly, but they cannot guarantee correctness.

Developers still need to:

- Write tests
- Think of edge cases
- Verify logic
- Debug failures
- Review code
- Measure coverage
- Check performance
- Validate security

This process is manual, repetitive, and time-consuming.

---

# Solution

Verix acts as an autonomous software quality engineer.

Given code or a repository, Verix will eventually:

- Understand the project
- Infer expected behavior
- Generate comprehensive test cases
- Execute tests safely
- Detect failures
- Explain bugs
- Suggest fixes
- Verify fixes
- Produce quality reports

---

# Target Users

- Individual developers
- AI-assisted programmers
- Startup engineering teams
- Open source maintainers
- Software engineering students

---

# Tech Stack

## Frontend

- Next.js
- React
- TypeScript
- CSS

## Backend

- FastAPI
- Python
- Pydantic
- Google GenAI SDK
- Docker
- GitHub public REST API

Future additions

- PostgreSQL
- Redis
- LangGraph
- Tree-sitter

Only when needed.

---

# Development Philosophy

Keep everything simple.

Do not overengineer.

Every technology must solve a real problem.

If a feature does not provide immediate value, postpone it.

Always build the smallest working version first.

---

# Current Version

## V0.1 — Complete

Goal:

Prove the end-to-end flow for submitting Python code and returning a test result.

Features:

- FastAPI health check at `GET /`
- `POST /generate` request validation for non-empty Python code
- Placeholder test response: `{"tests": "Coming soon"}`
- Next.js code-input page with loading, validation, error, and result states
- Local frontend-to-backend communication via CORS

NOT included:

- GitHub integration
- Docker execution
- LLM integration
- Repository analysis
- Multi-agent workflows
- Authentication
- Database
- Background jobs

V0.1 intentionally does not generate or execute tests. The placeholder response exists only to validate the client-server workflow before LLM integration.

## V0.2 — Complete

Goal:

Generate real Python unit tests with Gemini.

Features:

- Added a local environment-variable template for the Gemini API key.
- Created a backend Gemini service that generates pytest test code.
- Connected `POST /generate` to Gemini while preserving the existing API shape.
- Added safe API responses for missing configuration and Gemini failures.
- Verified the full browser-to-Gemini workflow.

V0.2 generates test code but does not run it. Test execution remains a later isolated Docker-based version.

## V0.3 — Complete

Goal:

Generate and safely execute pytest tests for submitted Python code.

Features:

- Added a local Docker image with pytest and a non-root execution user.
- Runs submitted code and Gemini-generated tests only in an isolated Docker container.
- Applies network isolation, a read-only filesystem, dropped capabilities, resource limits, and a 10-second timeout.
- Returns pytest output, the exit code, and timeout status from `POST /generate`.
- Displays generated tests and their execution outcome in the frontend.

V0.3 executes only within the local Docker runner; user code is never run directly on the host.

## V0.4 — Complete

Goal:

Accept a public GitHub repository URL and show its basic metadata.

Features:

- Added client- and server-side validation for public GitHub repository URLs.
- Added a backend service that fetches public metadata from GitHub's API without a token.
- Displays a repository's owner, name, description, primary language, stars, and GitHub link.
- Keeps repository lookup separate from the existing pasted-code generation flow.

V0.4 does not clone, download, inspect, or test repository files. Private repositories and authentication are not supported.

## V0.5 — Complete

Goal:

Understand the basic structure of a selected public GitHub repository.

Features:

- Fetches a repository's recursive file and directory tree through GitHub's public API.
- Displays a scrollable, indented repository structure in the frontend.
- Limits the displayed structure to 500 entries and reports when it is truncated.
- Shows GitHub's detected primary language with the repository metadata.

V0.5 reads repository metadata and paths only. It does not fetch file contents, clone repositories, install dependencies, or execute repository code.

## V0.6 — Complete

Goal:

Build focused context for public Python repositories and turn it into a transparent test plan.

Features:

- Fetches an allowlisted set of root-level Python configuration files when they exist.
- Identifies likely Python source and test paths from the bounded repository tree.
- Recognizes common Python project tools and test runners from configuration evidence.
- Produces an evidence-based, structured test plan with conservative suggested commands.
- Displays the detected setup, candidate counts, plan steps, and incomplete-tree warning in the frontend.

V0.6 does not retrieve arbitrary source or test-file contents, clone repositories, install dependencies, or execute repository code. GitHub access remains unauthenticated and is therefore subject to GitHub's public API rate limits.

## V0.7 — Complete

Goal:

Safely prepare a selected public Python repository and run its existing test suite.

Features:

- Consolidates metadata, tree, configuration, and test-plan retrieval into one repository-context request.
- Downloads the default branch as a bounded archive and safely extracts regular files into a temporary workspace.
- Rejects oversized, malformed, unsafe, empty, and non-Python repository archives.
- Installs supported root-level dependency declarations in a disposable Docker workspace.
- Runs pytest or tox with bounded CPU, memory, processes, output, and time.
- Disables network access and mounts the repository read-only during test execution.
- Returns preparation, dependency-installation, runner, and test-execution results to the frontend.

V0.7 supports public Python projects whose dependency and test-runner configuration is at the repository root. Nested Python projects in monorepositories are not selected automatically. Dependency installation may use the network inside its disposable container; the subsequent test run has no network access. Private repositories and authenticated GitHub access remain unsupported.

## V0.8 — Complete

Goal:

Generate focused repository-aware pytest tests, execute them safely, and keep their result separate from the repository's original test result.

Features:

- Adds deterministic backend regression tests for repository context, prompt construction, preparation, dependency setup, Docker execution, and API coordination.
- Deterministically selects one Python source target from the bounded tree, plus at most three related test files and three configuration files.
- Fetches only the selected UTF-8 contents, with a 64 KiB per-file limit and a 128 KiB total generation-context limit.
- Treats repository content as untrusted evidence and asks Gemini for one focused pytest module covering justified normal, boundary, and error behavior.
- Rejects empty, oversized, NUL-containing, or syntactically invalid generated Python before repository setup.
- Adds generated tests only to a disposable `.verix-generated-tests` directory without overwriting repository files.
- Runs the original suite first and the generated suite second in offline, resource-bounded Docker containers, preserving separate results. Tox repositories reuse one prepared default environment, preferring a Python-style environment name, for the focused generated run.
- Displays the selected target, generated code, dependency status, original-suite result, and generated-suite result in the frontend.

Repository source and test contents are sent to Gemini only after the user explicitly selects **Generate repository tests**. V0.8 remains limited to public default-branch Python repositories, one automatically selected target, and root-level project setup. It does not select a branch, commit, subdirectory, or target manually; persist or commit generated tests; measure coverage; investigate failures; propose fixes; retry automatically; or run an agent loop. Generated tests are evidence to review, not a guarantee of logical correctness.

---

# Roadmap

## V0.2

- Integrate LLM
- Generate real unit tests

## V0.3

- Execute generated tests safely inside Docker

## V0.4

- Accept public GitHub repository URLs

## V0.5

- Understand repository structure

## V0.6

- Repository context and test planning
- Fetch selected configuration-file contents and identify likely source and test paths
- Identify project setup and likely test targets
- Produce a structured testing plan

## V0.7

- Safe repository test execution
- Support public Python repositories first
- Consolidate repository context requests to reduce GitHub API usage
- Install declared dependencies and run existing tests in an isolated environment

## V0.8

- Repository-aware test generation
- Generate tests from selected repository context and conventions
- Run original and generated test suites separately

## V0.9

- Agentic investigation and explanation
- Plan, generate, execute, and investigate using structured evidence
- Explain failures and distinguish setup issues from code bugs

## V1.0

- Approval-based fix proposals and verified quality reports
- Propose minimal patches, rerun relevant tests, and report merge confidence

## After V1.0

- Support additional languages and test frameworks
- Add GitHub App integration for private repositories and pull requests
- Add performance and security review capabilities
- Add historical reports and CI integration

---

# Architecture Principles

- Frontend is responsible only for UI.
- Backend contains all business logic.
- Never expose API keys to the frontend.
- Never execute user code directly on the host machine.
- Every execution must eventually happen inside an isolated Docker container.
- Understand code and verify tests before proposing a fix.
- Every feature should be modular and easy to extend.

---

# Coding Principles

- Write readable code.
- Prefer clarity over cleverness.
- Keep functions small.
- Avoid duplicate logic.
- Use meaningful names.
- Explain complex code with comments.
- Add types wherever possible.
- Keep files focused on a single responsibility.

---

# Definition of Done

A feature is complete only when:

- It works correctly.
- It has been manually tested.
- Code is understandable.
- No unnecessary complexity was introduced.
- Documentation is updated.
- Reviewed changes are ready to commit and are committed only after user approval.

---

# Rules for AI (Codex)

`AGENTS.md` is the authoritative workflow and safety guide for AI coding agents. The active version and Current Task are maintained in `TODO.md`.

# Motto

Trust your code before you trust your AI.
