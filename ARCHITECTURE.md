# Verix Architecture

## Purpose

Verix is a small client-server application. Version 0.8 can generate and safely run pytest tests for pasted Python code. It can also inspect a public GitHub repository, build a transparent test plan, run the repository's existing pytest or tox suite, generate focused repository-aware tests with Gemini, and execute the original and generated suites separately in Docker.

## Current architecture

```text
Browser
  |
  v
Next.js frontend (localhost:3000)
  |                                      |
  | POST /repository/context             | POST /generate
  | POST /repository/test-run            v
  | POST /repository/generate         Gemini API
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
```

The frontend owns form state and rendering. The backend owns validation, GitHub access, test planning, repository preparation, Gemini access, and Docker orchestration. Submitted, generated, repository, dependency-build, and test code are never executed directly by a host Python process.

## Repository structure

```text
verix/
├── .gitignore
├── AGENTS.md
├── backend/
│   ├── Dockerfile
│   ├── main.py
│   ├── services/
│   │   ├── docker_runner.py
│   │   ├── github_service.py
│   │   ├── llm_service.py
│   │   ├── repository_preparer.py
│   │   └── repository_prompt.py
│   ├── tests/
│   │   ├── test_llm_service.py
│   │   ├── test_repository_prompt.py
│   │   └── test_repository_workflow.py
│   ├── requirements.txt
│   ├── .env.example
│   └── .gitignore
├── frontend/
│   ├── app/
│   │   ├── globals.css
│   │   ├── layout.tsx
│   │   └── page.tsx
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

The project deliberately keeps routes in one backend module and the interface in one page while each remains understandable. New layers should be introduced only when the current structure becomes difficult to maintain.

## Backend responsibilities

### API coordination

`backend/main.py` creates the FastAPI application, permits the local frontend through CORS, declares the request models, and coordinates the services. Invalid repository input becomes HTTP 422. Safe GitHub, Gemini, archive, preparation, or Docker infrastructure failures become HTTP 502. A missing Gemini key produces HTTP 503 on generation routes.

### GitHub evidence, planning, and generation context

`backend/services/github_service.py`:

- Accepts only canonical HTTPS URLs for public `github.com/owner/repository` repositories.
- Retrieves repository metadata and a recursive tree through GitHub's unauthenticated API.
- Returns at most 500 tree entries and marks an incomplete result as truncated.
- Fetches an allowlisted set of root-level Python configuration files.
- Infers likely Python source and test paths and excludes test-package initializer files from the test count.
- Recognizes Poetry, PDM, Hatch, Pipenv, setuptools, pip, pytest, and tox evidence.
- Builds a transparent test plan with setup-aware commands.
- Reuses metadata, tree, and configuration evidence in `/repository/context`.
- Selects one source target from the bounded tree. A non-`__init__.py` and non-`__main__.py` file with a directly named test is preferred, followed by the shallowest deterministic path.
- Selects at most three related test paths and three root configuration paths.
- Fetches selected UTF-8 source and test contents with a 64 KiB per-file limit and a 128 KiB total generation-context limit. Oversized optional files are skipped; an oversized selected source is rejected.

GitHub access uses `certifi` for its CA bundle. It remains unauthenticated and subject to GitHub's public rate limits.

### Repository prompt construction

`backend/services/repository_prompt.py` converts the bounded selection into deterministic JSON and clearly labels it as untrusted evidence rather than instructions. It escapes prompt-delimiter characters and asks for one pytest module covering source-justified normal, boundary, and error behavior without inventing dependencies or returning a patch.

### Repository preparation

`backend/services/repository_preparer.py` obtains the default-branch archive URL from GitHub, downloads the archive, and extracts it into a temporary directory as data only. It enforces these limits:

- 25 MiB compressed archive.
- 100 MiB total extracted regular-file data.
- 10,000 archive entries.
- Regular files and directories only; links and special entries are skipped.
- No absolute paths, parent traversal, duplicate destinations, or unexpected archive roots.

The prepared archive must contain Python source somewhere or a recognized Python configuration file at its root. The temporary preparation directory is removed after the request.

### Docker execution

`backend/services/docker_runner.py` supports pasted-code and repository flows.

For pasted code, it writes `main.py` and `test_generated.py` to a temporary directory and runs pytest in the local `verix-test-runner:dev` image. The container has no network, a read-only filesystem and workspace, dropped capabilities, no-new-privileges, PID and memory limits, a temporary `/tmp`, and a 10-second host timeout.

For repositories, it copies the safely extracted files into a second disposable workspace. Supported root-level dependency declarations include Poetry, PDM, Pipenv, requirements files, `pyproject.toml`, and `setup.py`. When `tox.ini` exists, tox environments and their declared dependencies are prepared. Dependency setup uses fixed backend-selected commands, a local `.verix-venv`, a writable disposable workspace, network access, and a 180-second timeout per command.

The original suite runs before any generated test file is added. Generated output must be non-empty, valid Python, free of NUL characters, and at most 128 KiB. It is written only to `.verix-generated-tests/test_verix_generated.py`; an existing reserved path is rejected instead of overwritten. The second execution focuses on that absolute container path. For tox, the runner lists the prepared default environments, prefers the first Python-style name such as `py313`, falls back to the first valid default name, and executes pytest inside only that environment rather than every configured lint or documentation environment. Other repositories use the prepared virtual environment's pytest.

Both test stages have no network, mount the repository read-only, and are limited to one CPU, 512 MiB of memory, 128 processes, and 60 seconds per container command. A tox-generated run first uses a separate bounded command to discover its prepared default environments, then uses another bounded command for pytest. Writable temporary mounts are provided for `/tmp`, the runner home, and tox work data. Returned output is capped at 50,000 characters. Named containers are force-removed after a host timeout. Docker startup failures become infrastructure errors instead of test failures.

Dependency installation is intentionally less restrictive because package downloads and build steps require network and workspace writes. It still runs in a disposable, resource-bounded container, but package installation is untrusted third-party code execution. The local Docker daemon is part of Verix's trusted boundary.

### LLM generation

`backend/services/llm_service.py` reads `LLM_API_KEY` from the ignored local environment file. It sends either pasted Python code or the bounded repository prompt to Gemini and requires a non-empty response. The key never reaches the frontend. Repository-generated output is validated before repository setup begins.

`backend/Dockerfile` supplies Python, pytest, tox, and the non-root `runner` user used by both execution flows.

## Frontend responsibilities

`frontend/app/page.tsx` is a single client component that provides:

- Public GitHub URL validation and repository-context loading.
- Metadata, bounded file-tree, and test-plan rendering.
- An explicit action to prepare and run the repository's existing tests.
- An explicit action to send focused repository contents to Gemini, then prepare and run original and generated tests separately.
- Preparation, dependency installation, skipped, failure, timeout, generated-code, and test-output states.
- Pasted Python input with Gemini generation and Docker execution results.
- Requests to `NEXT_PUBLIC_API_URL`, defaulting to `http://localhost:8000`.

`frontend/app/globals.css` contains the page styling. There are no reusable components yet because the interface has one page; small shared status logic remains local to that page.

## Main request flows

### Repository context

1. The browser validates a public GitHub URL.
2. `POST /repository/context` validates it again on the backend.
3. The GitHub service fetches metadata once, the recursive tree once, and only present allowlisted configuration files.
4. Paths, setup, the test plan, and a bounded generation selection are derived from that evidence.
5. The frontend displays the combined result. Source and test contents are not fetched or sent to Gemini at this stage.

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
2. `POST /repository/generate` recomputes the bounded selection and fetches only the selected source, related tests, and configuration contents.
3. The prompt builder marks repository data as untrusted evidence and asks Gemini for one focused pytest module.
4. The backend validates the generated module's content, size, and Python syntax.
5. The default-branch archive is independently downloaded and safely prepared.
6. Dependencies and any tox environments are installed with network access.
7. The original suite runs offline before the generated file exists.
8. The generated module is written to the disposable reserved directory and executed offline, using one prepared default tox environment when tox is selected or the prepared virtual environment's pytest otherwise.
9. The API and frontend keep the original and generated results separate.
10. All temporary repository copies and generated files are removed.

Ordinary test assertion failures return HTTP 200 with a non-zero return code. Installation failure also returns HTTP 200 and skips both suites. Repository validation failures return HTTP 422. GitHub, Gemini, archive, Docker, or invalid generated-output failures return HTTP 502. Missing Gemini configuration returns HTTP 503.

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

Returns metadata, tree, selected configuration files, and the derived test plan. Its `generation_selection` contains `target_path`, up to three `related_test_paths`, up to three `configuration_paths`, and `is_truncated`. This is the inspection endpoint used by the frontend.

### `POST /repository/test-run`

Returns:

- `preparation`: extracted file count, total bytes, and skipped archive entries.
- `installation`: return code, output, timeout state, and whether installation was skipped.
- `test_runner`: `pytest` or `tox`.
- `execution`: return code, output, timeout state, and whether tests were skipped.

### `POST /repository/generate`

Returns:

- `target_path`: the automatically selected Python source file.
- `generated_tests`: the validated Gemini-produced pytest module.
- `preparation`: extracted file count, total bytes, and skipped archive entries.
- `installation`: return code, output, timeout state, and whether installation was skipped.
- `test_runner`: `pytest` or `tox`.
- `existing_execution`: return code, output, timeout state, and skipped state for the original suite.
- `generated_execution`: the same fields for the focused generated suite.

## Configuration

The frontend uses `NEXT_PUBLIC_API_URL` and defaults to `http://localhost:8000`. The backend permits `http://localhost:3000` through CORS.

`backend/.env.example` documents `LLM_API_KEY`; the ignored `backend/.env` holds the local Gemini key. The key is required by `/generate` and `/repository/generate`, but not by repository inspection or `/repository/test-run`. The Docker image must exist locally as `verix-test-runner:dev`, and Docker Desktop must be running.

## V0.8 boundaries

- Public GitHub repositories only; no token, private repository, or pull-request integration.
- Python projects only, with dependency declarations and runner configuration at the repository root.
- One automatically selected source target; no manual target, branch, commit, or nested-project selection.
- The bounded 500-entry tree can make selection incomplete in large repositories.
- Repository context and the archive are fetched separately from the current default branch rather than pinned to one commit, so a branch update between the two operations can create a snapshot mismatch.
- Generated tests are temporary, are not committed back, and are not guaranteed to be logically correct.
- No coverage measurement, failure investigation, fix proposal, retries, or agent loop.
- No database, Redis, queue, authentication, or background job system.
- Requests are synchronous, and one backend process coordinates the local Docker daemon directly.
- Docker isolation is intended for local development, not as a production-grade multi-tenant security boundary.

## Next evolution

V0.9 will classify repository workflow outcomes and use bounded execution evidence to explain failures. It will not automatically modify code, retry, or apply fixes. Approval-based patches and verification remain V1.0 work.
