# Verix Architecture

## Purpose

Verix is a small client-server application. Version 0.10 can generate and safely run pytest tests for pasted Python code. For public Python repositories, it supports a validated branch, tag, or commit reference; a validated project subdirectory; a verified source-target choice; a bounded Gemini-context preview; safe Docker execution; and a bounded investigation explanation.

## Current architecture

```text
Browser
  |
  v
Next.js page and feature components (localhost:3000)
  |
  v
repository workflow hook -> typed API client
  |                                      |
  | POST /repository/context             | POST /generate
  | POST /repository/context/preview     v
  | POST /repository/test-run            v
  | POST /repository/generate         Gemini API
  | POST /repository/investigate      |
  v                                      |
FastAPI backend                          | generated pytest code
  |                                      v
  | repository evidence/archive      Docker pasted-code runner
  v                                      |
GitHub public API                        v
  |                                  execution result
  | selected bounded contents
  v
repository-aware prompt -> Gemini
  |
  | generated pytest module
  v
safe temporary repository copy
  |
  | dependency installation in Docker (network allowed)
  | original pytest/tox run in Docker (offline)
  | generated pytest run in Docker (offline)
  v
separate original and generated results
  |
  v
bounded evidence -> deterministic outcome -> Gemini explanation
```

The frontend owns form state and rendering. The backend API owns HTTP validation and response translation, workflows coordinate use cases, services handle external systems and execution policies, and domain models carry internal data between those boundaries. Submitted, generated, repository, dependency-build, and test code are never executed directly by a host Python process.

## Repository structure

```text
verix/
├── .gitignore
├── AGENTS.md
├── backend/
│   ├── Dockerfile
│   ├── main.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── presenters.py
│   │   └── schemas.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── execution.py
│   │   ├── investigation.py
│   │   └── repository.py
│   ├── services/
│   │   ├── docker_commands.py
│   │   ├── docker_executor.py
│   │   ├── docker_runner.py
│   │   ├── github_client.py
│   │   ├── github_service.py
│   │   ├── llm_service.py
│   │   ├── repository_analyzer.py
│   │   ├── repository_dependencies.py
│   │   ├── repository_investigation.py
│   │   ├── repository_investigation_prompt.py
│   │   ├── repository_preparer.py
│   │   ├── repository_prompt.py
│   │   ├── repository_test_commands.py
│   │   └── repository_workspace.py
│   ├── tests/
│   │   ├── test_api_presenters.py
│   │   ├── test_api_schemas.py
│   │   ├── test_docker_commands.py
│   │   ├── test_docker_executor.py
│   │   ├── test_github_client.py
│   │   ├── test_llm_service.py
│   │   ├── test_repository_dependencies.py
│   │   ├── test_repository_investigation.py
│   │   ├── test_repository_prompt.py
│   │   ├── test_repository_test_commands.py
│   │   ├── test_repository_workflow.py
│   │   └── test_repository_workspace.py
│   ├── workflows/
│   │   ├── __init__.py
│   │   ├── repository_execution.py
│   │   └── repository_investigation.py
│   ├── requirements.txt
│   ├── .env.example
│   └── .gitignore
├── frontend/
│   ├── app/
│   │   ├── globals.css
│   │   ├── layout.tsx
│   │   └── page.tsx
│   ├── components/
│   │   ├── pasted-code-generator.tsx
│   │   ├── repository-execution-results.tsx
│   │   └── repository-inspection.tsx
│   ├── hooks/
│   │   └── use-repository-workflow.ts
│   ├── lib/
│   │   └── api.ts
│   ├── types/
│   │   └── api.ts
│   ├── package.json
│   ├── package-lock.json
│   ├── next-env.d.ts
│   ├── tsconfig.json
│   ├── next.config.ts
│   └── .gitignore
├── PROJECT.md
├── ARCHITECTURE.md
├── README.md
└── TODO.md
```

The route declarations remain together in `backend/main.py`, and the browser still renders one page. The implementation behind those entry points is split by reason to change: HTTP contracts, domain data, use-case coordination, external access, safety policies, process execution, interface state, and presentation. These are focused boundaries rather than framework layers; new structure should still be introduced only when a current responsibility has become difficult to maintain or test.

## Backend responsibilities

### API coordination

`backend/main.py` creates the FastAPI application, permits the local frontend through CORS, declares the routes, and translates expected failures into HTTP responses. `backend/api/schemas.py` owns Pydantic request models, including validated repository references, subdirectories, and source targets. `backend/api/presenters.py` converts internal repository models into JSON-ready response dictionaries. Invalid repository input becomes HTTP 422. Safe GitHub, Gemini, archive, preparation, or Docker infrastructure failures become HTTP 502. A missing Gemini key produces HTTP 503 on generation routes.

`backend/workflows/repository_execution.py` coordinates repository preparation, dependency installation, and existing/generated test execution. `backend/workflows/repository_investigation.py` coordinates one plan-generate-execute-classify-explain pass without retrying or modifying code. `backend/models/repository.py`, `backend/models/execution.py`, and `backend/models/investigation.py` carry internal data between those boundaries.

### GitHub evidence, planning, and generation context

Repository inspection is divided into three focused services:

- `backend/services/github_client.py` performs bounded GitHub HTTP requests, response decoding, content decoding, and transport-error handling.
- `backend/services/github_service.py` validates repository URLs and coordinates metadata, tree, configuration, context, and selected-content retrieval.
- `backend/services/repository_analyzer.py` applies deterministic rules to infer paths, detect Python tooling, build the test plan, and choose bounded generation context.

Together, these modules provide a repository flow that:

- Accepts only canonical HTTPS URLs for public `github.com/owner/repository` repositories.
- Retrieves repository metadata and a recursive tree through GitHub's unauthenticated API.
- Returns at most 500 tree entries and marks an incomplete result as truncated.
- Fetches an allowlisted set of root-level Python configuration files.
- Infers likely Python source and test paths and excludes test-package initializer files from the test count.
- Recognizes Poetry, PDM, Hatch, Pipenv, setuptools, pip, pytest, and tox evidence.
- Builds a transparent test plan with setup-aware commands.
- Resolves the default branch, or one selected branch, tag, or commit reference, to a validated immutable commit SHA.
- Restricts a selected subdirectory to one safe repository-relative directory and filters the tree before choosing source, test, and configuration paths.
- Restricts a selected target to one verified Python source blob inside the selected project directory.
- Uses the same resolved SHA for the tree, configuration files, selected source/test contents, and archive URL in repository generation and investigation.
- Reuses metadata, tree, and configuration evidence in `/repository/context`.
- Selects one source target from the bounded tree. A non-`__init__.py` and non-`__main__.py` file with a directly named test is preferred, followed by the shallowest deterministic path.
- Selects at most three related test paths and three root configuration paths.
- Fetches selected UTF-8 source and test contents with a 64 KiB per-file limit and a 128 KiB total generation-context limit. Oversized optional files are skipped; an oversized selected source is rejected.

GitHub access uses `certifi` for its CA bundle. It remains unauthenticated and subject to GitHub's public rate limits.

### Repository prompt construction

`backend/services/repository_prompt.py` converts the bounded selection into deterministic JSON and clearly labels it as untrusted evidence rather than instructions. It includes both the full repository path and the project-relative target path, because Docker runs from the selected project directory. It escapes prompt-delimiter characters and asks for one pytest module covering source-justified normal, boundary, and error behavior without inventing dependencies or returning a patch.

`backend/services/repository_investigation.py` turns completed installation and test facts into bounded evidence and one deterministic outcome. `backend/services/repository_investigation_prompt.py` sends that outcome and no more than 2,000 characters of output per command to Gemini. Repository data and command output are marked as untrusted evidence, not instructions.

### Repository preparation

`backend/services/repository_preparer.py` obtains a validated archive URL for a resolved commit SHA, downloads the archive, and extracts it into a temporary directory as data only. When requested, it safely selects the validated project subdirectory as the Docker workspace root. `backend/services/repository_workspace.py` owns the second disposable repository copy, generated-test validation, and the reserved generated-test path. Preparation enforces these limits:

- 25 MiB compressed archive.
- 100 MiB total extracted regular-file data.
- 10,000 archive entries.
- Regular files and directories only; links and special entries are skipped.
- No absolute paths, parent traversal, duplicate destinations, or unexpected archive roots.

The prepared archive must contain Python source somewhere or a recognized Python configuration file at its root. The temporary preparation directory is removed after the request.

### Docker execution

Docker execution is split into four responsibilities:

- `backend/services/docker_runner.py` coordinates pasted-code and repository execution.
- `backend/services/docker_commands.py` assembles the fixed, security-bounded Docker commands.
- `backend/services/docker_executor.py` starts processes, captures bounded output, handles timeouts, and cleans up named containers.
- `backend/services/repository_dependencies.py` and `backend/services/repository_test_commands.py` select trusted dependency and test commands from repository evidence; they never accept repository-provided shell commands.

For pasted code, it writes `main.py` and `test_generated.py` to a temporary directory and runs pytest in the local `verix-test-runner:dev` image. The container has no network, a read-only filesystem and workspace, dropped capabilities, no-new-privileges, PID and memory limits, a temporary `/tmp`, and a 10-second host timeout.

For repositories, the workspace manager copies the safely extracted files into a second disposable workspace. Supported root-level dependency declarations include Poetry, PDM, Pipenv, requirements files, `pyproject.toml`, and `setup.py`. When `tox.ini` exists, tox environments and their declared dependencies are prepared. Dependency setup uses fixed backend-selected commands, a local `.verix-venv`, a writable disposable workspace, network access, and a 180-second timeout per command.

The original suite runs before any generated test file is added. Generated output must be non-empty, valid Python, free of NUL characters, and at most 128 KiB. It is written only to `.verix-generated-tests/test_verix_generated.py`; an existing reserved path is rejected instead of overwritten. The second execution focuses on that absolute container path. For tox, the runner lists the prepared default environments, prefers the first Python-style name such as `py313`, falls back to the first valid default name, and executes pytest inside only that environment rather than every configured lint or documentation environment. Other repositories use the prepared virtual environment's pytest.

Both test stages have no network, mount the repository read-only, and are limited to one CPU, 512 MiB of memory, 128 processes, and 60 seconds per container command. A tox-generated run first uses a separate bounded command to discover its prepared default environments, then uses another bounded command for pytest. Writable temporary mounts are provided for `/tmp`, the runner home, and tox work data. Returned output is capped at 50,000 characters. Named containers are force-removed after a host timeout. Docker startup failures become infrastructure errors instead of test failures.

Dependency installation is intentionally less restrictive because package downloads and build steps require network and workspace writes. It still runs in a disposable, resource-bounded container, but package installation is untrusted third-party code execution. The local Docker daemon is part of Verix's trusted boundary.

### LLM generation

`backend/services/llm_service.py` reads `LLM_API_KEY` from the ignored local environment file. It sends either pasted Python code, the bounded repository test prompt, or bounded investigation evidence to Gemini and requires a non-empty response. SDK request failures are normalized to safe backend errors. Investigation explanations are capped at 4,000 characters. The key never reaches the frontend. Repository-generated output is validated before repository setup begins.

`backend/Dockerfile` supplies Python, pytest, tox, and the non-root `runner` user used by both execution flows.

## Frontend responsibilities

`frontend/app/page.tsx` composes the pasted-code, repository execution, repository generation, V0.9 investigation, and V0.10 targeting workflows. Its supporting modules are:

- `frontend/hooks/use-repository-workflow.ts`, which owns repository form state and user actions.
- `frontend/lib/api.ts`, which owns typed backend HTTP calls and API-error extraction.
- `frontend/types/api.ts`, which defines response types shared by the hook and components.
- `frontend/components/repository-inspection.tsx`, which renders metadata, the bounded tree, and the test plan.
- `frontend/components/repository-execution-results.tsx`, which renders existing and generated execution results separately.
- `frontend/components/pasted-code-generator.tsx`, which owns the pasted-code form, request state, and results.

Together they provide:

- Public GitHub URL validation and repository-context loading.
- Metadata, bounded file-tree, and test-plan rendering.
- An explicit action to prepare and run the repository's existing tests.
- An explicit action to send focused repository contents to Gemini, then prepare and run original and generated tests separately.
- An explicit **Investigate repository** action that performs one full V0.9 pass and displays a classified outcome with its Gemini explanation.
- Optional reference and project-folder inputs, a verified source-target selector, and a preview of the bounded Gemini context before repository generation.
- Preparation, dependency installation, skipped, failure, timeout, generated-code, and test-output states.
- Pasted Python input with Gemini generation and Docker execution results.
- Requests to `NEXT_PUBLIC_API_URL`, defaulting to `http://localhost:8000`.

`frontend/app/globals.css` contains the page styling. The split keeps request/state logic separate from result rendering without introducing a state library or additional framework.

## Main request flows

### Repository context

1. The browser submits a public GitHub URL plus optional reference and subdirectory values.
2. `POST /repository/context` validates every value and resolves the reference to one commit SHA.
3. The GitHub service fetches metadata once, filters the recursive tree to the selected project directory when present, and fetches only present allowlisted configuration files.
4. Paths, setup, the test plan, and a bounded generation selection are derived from that evidence.
5. The frontend lets the user retain the automatic target or select another verified source path. `POST /repository/context/preview` returns only the exact bounded content for that target; it does not call Gemini or run code.

The older focused repository endpoints remain available, but the frontend uses the consolidated endpoint to avoid duplicate requests.

### Repository test run

1. The user explicitly selects **Run repository tests**.
2. `POST /repository/test-run` resolves and downloads the repository's default-branch archive.
3. The preparer safely extracts and validates it in a temporary directory.
4. The runner creates a writable disposable copy and a `.verix-venv` when dependencies are declared.
5. Dependency commands run in resource-bounded containers with network access.
6. pytest or tox runs in a new resource-bounded container with no network and a read-only repository mount.
7. The API returns preparation, installation, runner, and execution results.
8. Both temporary repository directories are removed.

### Repository-aware generation

1. The user explicitly selects **Generate repository tests**.
2. `POST /repository/generate` uses the selected SHA, optional project directory, and verified source target to fetch only the selected source, related tests, and configuration contents.
3. The prompt builder marks repository data as untrusted evidence and asks Gemini for one focused pytest module.
4. The backend validates the generated module's content, size, and Python syntax.
5. The default-branch archive is independently downloaded and safely prepared.
6. Dependencies and any tox environments are installed with network access.
7. The original suite runs offline before the generated file exists.
8. The generated module is written to the disposable reserved directory and executed offline, using one prepared default tox environment when tox is selected or the prepared virtual environment's pytest otherwise.
9. The API and frontend keep the original and generated results separate.
10. All temporary repository copies and generated files are removed.

Ordinary test assertion failures return HTTP 200 with a non-zero return code. Installation failure also returns HTTP 200 and skips both suites. Repository validation failures return HTTP 422. GitHub, Gemini, archive, Docker, or invalid generated-output failures return HTTP 502. Missing Gemini configuration returns HTTP 503.

### Repository investigation

1. The user explicitly selects **Investigate repository**.
2. `POST /repository/investigate` fetches the planned generation context, resolving the default branch to one immutable commit SHA.
3. Gemini generates one focused pytest module; Verix validates it before any repository setup.
4. The archive for that same SHA is safely prepared; Docker uses the selected project folder as its workspace when one was chosen, and both suites run separately.
5. The backend converts the installation and execution facts into bounded evidence, then selects one fixed outcome category.
6. Gemini receives the fixed outcome and bounded evidence to produce a concise explanation; it cannot change the outcome or request a retry.
7. The API returns the plan, generated tests, separate execution results, outcome, and explanation. The frontend displays them.

The workflow has no automatic retry, patch, or fix step. An ordinary test failure or no-existing-tests result remains an HTTP 200 result with an outcome label. Invalid repository input returns HTTP 422. Gemini, GitHub, archive, validation, or Docker infrastructure failures return HTTP 502; a missing Gemini key returns HTTP 503.

### Pasted-code generation

1. The browser sends non-empty Python code to `POST /generate`.
2. Gemini returns pytest source.
3. The backend writes the submitted and generated code to a temporary workspace.
4. pytest runs in Docker without network access.
5. Generated tests and execution details return to the browser.

## API contract

### `GET /`

Returns `{"message": "Verix API is running"}`.

### `POST /generate`

Accepts `{"code": "..."}` and returns generated pytest source plus `return_code`, `output`, and `timed_out` execution fields.

### Focused repository endpoints

All accept `{"url": "https://github.com/owner/repository"}`:

- `POST /repository` returns metadata.
- `POST /repository/tree` returns the bounded recursive tree.
- `POST /repository/configuration` returns allowlisted root configuration contents.
- `POST /repository/paths` returns likely Python source and test paths.
- `POST /repository/setup` returns detected project and test tooling.
- `POST /repository/test-plan` returns the evidence-based test plan.

### `POST /repository/context`

Accepts `url` plus optional `reference`, `subdirectory`, and `target_path`. It returns the resolved `revision`, selected `subdirectory`, metadata, tree, selected configuration files, and derived test plan. Its `generation_selection` contains `target_path`, up to three `related_test_paths`, up to three `configuration_paths`, and `is_truncated`. This is the inspection endpoint used by the frontend.

### `POST /repository/context/preview`

Requires `url` and a verified `target_path`, with optional `reference` and `subdirectory`. It returns the resolved revision, selection, source content, related existing-test contents, configuration contents, skipped paths, and total bounded context size. It never calls Gemini or Docker.

### `POST /repository/test-run`

Accepts `url` plus optional `reference` and `subdirectory`, then returns:

- `preparation`: extracted file count, total bytes, and skipped archive entries.
- `installation`: return code, output, timeout state, and whether installation was skipped.
- `test_runner`: `pytest` or `tox`.
- `execution`: return code, output, timeout state, and whether tests were skipped.

### `POST /repository/generate`

Accepts `url` plus optional `reference`, `subdirectory`, and `target_path`, then returns:

- `target_path`: the automatically selected Python source file.
- `generated_tests`: the validated Gemini-produced pytest module.
- `preparation`: extracted file count, total bytes, and skipped archive entries.
- `installation`: return code, output, timeout state, and whether installation was skipped.
- `test_runner`: `pytest` or `tox`.
- `existing_execution`: return code, output, timeout state, and skipped state for the original suite.
- `generated_execution`: the same fields for the focused generated suite.

### `POST /repository/investigate`

Accepts the same targeting fields as `/repository/generate` and returns the generated-test response fields plus `test_plan` and:

```json
{
  "investigation": {
    "outcome": "no_existing_tests",
    "explanation": "The repository did not have an existing pytest suite to run."
  }
}
```

Possible outcomes are `setup_failed`, `no_existing_tests`, `existing_tests_timed_out`, `existing_tests_failed`, `generated_tests_timed_out`, `generated_tests_failed`, and `tests_passed`.

## Configuration

The frontend uses `NEXT_PUBLIC_API_URL` and defaults to `http://localhost:8000`. The backend permits `http://localhost:3000` through CORS.

`backend/.env.example` documents `LLM_API_KEY`; the ignored `backend/.env` holds the local Gemini key. The key is required by `/generate`, `/repository/generate`, and `/repository/investigate`, but not by repository inspection or `/repository/test-run`. The Docker image must exist locally as `verix-test-runner:dev`, and Docker Desktop must be running.

## V0.10 boundaries

- Public GitHub repositories only; no token, private repository, or pull-request integration.
- Python projects only, with dependency declarations and runner configuration at the selected project root.
- Optional branch, tag, full commit SHA, project subdirectory, and verified Python source target selection.
- The bounded 500-entry tree can make selection incomplete in large repositories.
- Repository context, generation, test execution, and investigation resolve the requested reference to one commit SHA before their selected work begins.
- Generated tests are temporary, are not committed back, and are not guaranteed to be logically correct.
- Investigation explanations are limited to the collected evidence; they are not guaranteed root-cause diagnoses.
- No coverage measurement, fix proposal, automatic retry, patch application, or multi-step agent loop.
- No database, Redis, queue, authentication, or background job system.
- Requests are synchronous, and one backend process coordinates the local Docker daemon directly.
- Docker isolation is intended for local development, not as a production-grade multi-tenant security boundary.

## Next evolution

Approval-based patches and verification remain V1.0 work.
