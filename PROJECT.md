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
- Tailwind CSS

## Backend

- FastAPI
- Python

Future additions

- Docker
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

## V0.1

Goal:

Generate unit tests from a pasted Python function.

Features:

- Accept Python code
- Send code to backend
- Generate placeholder tests
- Display generated tests

NOT included:

- GitHub integration
- Docker execution
- LLM integration
- Repository analysis
- Multi-agent workflows
- Authentication
- Database
- Background jobs

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

- Multi-agent workflow

## V0.7

- Automatic bug fixing

## V0.8

- Performance analysis

## V0.9

- Security analysis

## V1.0

AI Software Quality Engineer

---

# Architecture Principles

- Frontend is responsible only for UI.
- Backend contains all business logic.
- Never expose API keys to the frontend.
- Never execute user code directly on the host machine.
- Every execution must eventually happen inside an isolated Docker container.
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