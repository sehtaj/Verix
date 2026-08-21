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

- [x] Consolidate repository context fetching to reduce duplicate GitHub API requests
- [x] Prepare a selected public Python repository for isolated test execution
- [x] Extend the isolated Docker runner for repository test runs
- [x] Install declared repository dependencies inside the isolated environment
- [x] Run the existing repository test suite with bounded resources
- [x] Return repository test execution results
- [x] Display repository test execution results
- [x] Test the V0.7 flow
- [x] Update README during the V0.7 Review Phase

---

## V0.8

- [x] Add deterministic backend regression tests for the V0.7 repository workflow
- [x] Select a bounded repository source target and relevant context files
- [x] Fetch bounded source and existing-test contents for the selected target
- [x] Build a repository-aware test-generation prompt from verified context
- [x] Generate pytest tests for the selected repository target
- [x] Add generated tests to the disposable repository workspace without overwriting files
- [x] Run generated tests alongside the existing suite while preserving separate results
- [x] Return repository-generated tests and their execution results
- [x] Display repository-generated tests and execution results
- [x] Test the complete V0.8 flow
- [x] Update documentation during the V0.8 Review Phase

---

## V0.9

- [x] Define structured repository workflow outcomes and bounded investigation evidence, including no-existing-tests results
- [x] Pin repository context and execution archives to one commit revision
- [x] Classify setup failures, no-existing-tests results, existing-suite failures, generated-suite failures, and timeouts
- [x] Build an evidence-grounded repository investigation prompt
- [x] Generate a bounded failure explanation with Gemini
- [x] Coordinate one plan-generate-execute-investigate pass without automatic retries or fixes
- [x] Return the structured classification and explanation
- [x] Display repository investigation results
- [x] Add deterministic regression tests for the investigation flow
- [x] Test the complete V0.9 flow
- [x] Update documentation during the V0.9 Review Phase

---

## V0.10

- [x] Define safe repository reference, subdirectory, and source-target selection inputs
- [x] Fetch GitHub context and archives from the selected commit revision
- [x] Support validated repository subdirectory selection
- [x] Support validated manual Python source-target selection
- [x] Preview the selected repository target and bounded Gemini context in the frontend
- [x] Propagate the selected target through generation and isolated execution
- [x] Add deterministic regression tests for repository targeting
- [x] Test the complete V0.10 flow
- [x] Update documentation during the V0.10 Review Phase

---

## V0.11

- [x] Define an approval-based fix-proposal contract and safety boundary
- [x] Select bounded failure-focused repository context for a proposed fix
- [x] Generate one minimal proposed patch without applying it
- [x] Validate and display a proposed patch for explicit user review
- [x] Add deterministic regression tests for fix proposals
- [x] Test the complete V0.11 flow
- [x] Update documentation during the V0.11 Review Phase

---

## V0.12

- [ ] Define an explicit approval/apply request contract
- [ ] Apply an approved validated patch only in a disposable workspace
- [ ] Rerun the relevant repository tests after applying the patch
- [ ] Return verified post-patch results without changing GitHub
- [ ] Add deterministic regression tests for approved patch execution
- [ ] Test the complete V0.12 flow
- [ ] Update documentation during the V0.12 Review Phase

---

## Current Task

**Define an explicit approval/apply request contract**

---

## Notes

Codex may update this file throughout development to keep it accurate.
