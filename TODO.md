# TODO

> **Owner:** Codex
>
> This file should always reflect the current state of development.

## Rules

- Mark completed tasks automatically.
- Add newly discovered tasks when necessary.
- Remove obsolete tasks.
- Reorder tasks if a better implementation order is found.
- Keep tasks small enough to finish in one commit.
- Never work on future versions unless explicitly instructed.
- Always keep **Current Task** updated.
- If all tasks are complete, suggest the next milestone instead of implementing it automatically.

---

## V0.1

- [x] Set up FastAPI backend
- [x] Add health endpoint
- [x] Create generate endpoint
- [x] Set up Next.js frontend
- [x] Build code input page
- [x] Connect frontend to backend
- [x] Display backend response
- [x] Add basic validation
- [x] Test complete workflow
- [x] Update README

---

## V0.2

- [x] Add environment variables
- [x] Create LLM service
- [x] Connect `/generate` to the LLM service
- [x] Replace the placeholder response with generated tests
- [x] Handle LLM API errors
- [x] Test the V0.2 flow

---

## V0.3

- [x] Add Docker test runner image
- [x] Create isolated test execution service
- [x] Run generated tests with a timeout
- [x] Return test execution results
- [x] Display test execution results
- [x] Test the V0.3 flow
- [x] Update README

---

## V0.4

- [x] Add a GitHub repository URL input
- [x] Validate public GitHub repository URLs
- [x] Fetch basic repository metadata
- [x] Display the selected repository details
- [x] Test the V0.4 flow
- [x] Update README

---

## V0.5

- [x] Fetch the selected repository's file tree
- [x] Display the repository file structure
- [x] Detect the repository's primary language
- [x] Test the V0.5 flow
- [x] Update README

---

## V0.6

- [x] Fetch relevant repository configuration file contents
- [x] Identify likely source and test paths from the repository tree
- [x] Detect Python project setup from configuration files
- [x] Generate a structured repository test plan
- [x] Display the repository test plan
- [x] Test the V0.6 flow
- [x] Update README

---

## V0.7

- [ ] Consolidate repository context fetching to reduce duplicate GitHub API requests
- [ ] Prepare a selected public Python repository for isolated test execution
- [ ] Extend the isolated Docker runner for repository test runs
- [ ] Install declared repository dependencies inside the isolated environment
- [ ] Run the existing repository test suite with bounded resources
- [ ] Return repository test execution results
- [ ] Display repository test execution results
- [ ] Test the V0.7 flow
- [ ] Update README

---

## Current Task

**Consolidate repository context fetching to reduce duplicate GitHub API requests**

---

## Notes

Codex may update this file throughout development to keep it accurate.
