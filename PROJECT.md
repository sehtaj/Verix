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
- Google GenAI SDK
- Docker

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

---

# Roadmap

## V0.2

- Integrate LLM
- Generate real unit tests

## V0.3

- Execute generated tests safely inside Docker

## V0.4

- Upload GitHub repositories

## V0.5

- Understand repository structure

## V0.6

- Repository context and test planning
- Fetch relevant configuration, source, and test-file contents
- Identify project setup and likely test targets
- Produce a structured testing plan

## V0.7

- Safe repository test execution
- Support public Python repositories first
- Install declared dependencies and run existing tests in an isolated environment

## V0.8

- Repository-aware test generation
- Generate tests from selected repository context and conventions
- Run generated tests with the existing test suite

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
- Changes are committed to Git.

---

# Rules for AI (Codex)

Before making changes:

1. Read PROJECT.md.
2. Only implement the current version.
3. Never implement future roadmap items.
4. Keep the architecture simple.
5. Explain every major architectural decision.
6. Prefer maintainability over clever solutions.
7. Do not add dependencies unless required.
8. If uncertain, ask instead of assuming.

# Motto

Trust your code before you trust your AI.
