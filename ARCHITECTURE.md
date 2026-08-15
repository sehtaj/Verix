# Verix Architecture

## Purpose

Verix is a small client-server application. Version 0.7 can generate and safely run pytest tests for pasted Python code. It can also inspect a public GitHub repository, build a test plan, prepare a bounded repository archive, install supported dependencies, and run the repository's existing pytest or tox suite in Docker.

## Current architecture

```text
Browser
  |
  v
Next.js frontend (localhost:3000)
  |                                      |
  | POST /repository/context             | POST /generate
  | POST /repository/test-run            v
  v                                  Gemini API
FastAPI backend                           |
  |                                      | generated pytest code
  | repository evidence/archive          v
  v                                  Docker pasted-code runner
GitHub public API                         |
  |                                      v
  | bounded repository archive       execution result
  v
safe temporary repository copy
  |
  | dependency installation in Docker
  | existing pytest/tox run in Docker
  v
repository execution result
```

The frontend owns form state and rendering. The backend owns validation, GitHub access, test planning, repository preparation, Gemini access, and Docker orchestration. Submitted code and repository code are never executed directly by a host Python process.

## Repository structure

```text
verix/
├── backend/
│   ├── Dockerfile
│   ├── main.py
│   ├── services/
│   │   ├── github_service.py
│   │   ├── llm_service.py
│   │   ├── repository_preparer.py
│   │   └── test_runner.py
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

`backend/main.py` creates the FastAPI application, permits the local frontend through CORS, declares the request models, and coordinates the services. Invalid repository input becomes HTTP 422. Safe upstream or preparation failures become HTTP 502. A missing Gemini key produces HTTP 503.

### GitHub evidence and planning

`backend/services/github_service.py`:

- Accepts only canonical HTTPS URLs for public `github.com/owner/repository` repositories.
- Retrieves repository metadata and a recursive tree through GitHub's unauthenticated API.
- Returns at most 500 tree entries and marks an incomplete result as truncated.
- Fetches an allowlisted set of root-level Python configuration files.
- Infers likely Python source and test paths.
- Recognizes Poetry, PDM, Hatch, Pipenv, setuptools, pip, pytest, and tox evidence.
- Builds a transparent test plan with setup-aware commands.
- Reuses metadata, tree, and configuration evidence in `/repository/context` instead of repeating the same GitHub requests.

GitHub access uses `certifi` for its CA bundle. It remains unauthenticated and subject to GitHub's public rate limits.

### Repository preparation

`backend/services/repository_preparer.py` obtains the default-branch archive URL from GitHub, downloads the archive, and extracts it into a temporary directory as data only. It enforces these limits:

- 25 MiB compressed archive
- 100 MiB total extracted regular-file data
- 10,000 archive entries
- Regular files and directories only; links and special entries are skipped
- No absolute paths, parent traversal, duplicate destinations, or unexpected archive roots

The prepared archive must contain Python source somewhere or a recognized Python configuration file at its root. The temporary preparation directory is removed after the request.

### Docker execution

`backend/services/test_runner.py` supports two related flows.

For pasted code, it writes `main.py` and `test_generated.py` to a temporary directory and runs pytest in the local `verix-test-runner:dev` image. The container has no network, a read-only filesystem and workspace, dropped capabilities, no-new-privileges, PID and memory limits, a temporary `/tmp`, and a 10-second host timeout.

For repositories, it copies the safely extracted files into a second disposable workspace. Supported root-level dependency declarations include Poetry, PDM, Pipenv, requirements files, `pyproject.toml`, and `setup.py`. When `tox.ini` exists, tox environments and their declared dependencies are also prepared during this stage. Dependency setup uses fixed backend-selected commands, a local `.verix-venv`, a writable disposable workspace, and network access inside the container. Each installation command has a 180-second timeout.

After installation, tox is selected when a root `tox.ini` exists; otherwise pytest discovery is used. A prepared tox environment is retained in a reserved directory inside the disposable workspace and mounted separately as writable tox work data during the test run. The test container has no network, mounts the repository itself read-only, and is limited to one CPU, 512 MiB of memory, 128 processes, and 60 seconds. Writable temporary mounts are provided for `/tmp` and the runner home. Returned command output is capped at 50,000 characters. Named containers are force-removed after a host timeout.

The dependency-installation stage is intentionally less restrictive than the test stage because package downloads and build steps require network and workspace writes. Those steps still run in a disposable, resource-bounded container, but package installation should be treated as execution of untrusted third-party build code. The local Docker daemon is part of Verix's trusted boundary.

### LLM generation

`backend/services/llm_service.py` reads `LLM_API_KEY` from the ignored local environment file, sends pasted Python code to Gemini, and returns pytest code that imports submitted symbols from `main`. The key never reaches the frontend.

`backend/Dockerfile` supplies Python, pytest, tox, and the non-root `runner` user used by both execution flows.

## Frontend responsibilities

`frontend/app/page.tsx` is a single client component that provides:

- Public GitHub URL validation and repository-context loading.
- Metadata, bounded file-tree, and evidence-based test-plan rendering.
- An explicit action to prepare the selected repository and run its existing tests.
- Preparation, dependency installation, skipped, failure, timeout, and test output states.
- Pasted Python input with Gemini generation and Docker execution results.
- Requests to `NEXT_PUBLIC_API_URL`, defaulting to `http://localhost:8000`.

`frontend/app/globals.css` contains the page styling. There are no reusable components yet because the interface has one page and no meaningful duplicated UI logic.

## Main request flows

### Repository context

1. The browser validates a public GitHub URL.
2. `POST /repository/context` validates it again on the backend.
3. The GitHub service fetches metadata once, the recursive tree once, and only present allowlisted configuration files.
4. Paths, setup, and the test plan are derived from that shared evidence.
5. The frontend displays the combined result.

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

Test assertion failures are normal results: the API returns HTTP 200 with a non-zero test return code. Installation failures also return HTTP 200 and mark test execution as skipped. Validation problems return HTTP 422, while infrastructure or upstream failures return HTTP 502.

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

Returns metadata, tree, selected configuration files, and the derived test plan in one response. This is the repository-inspection endpoint used by the frontend.

### `POST /repository/test-run`

Returns:

- `preparation`: extracted file count, total bytes, and skipped archive entries.
- `installation`: return code, output, timeout state, and whether installation was skipped.
- `test_runner`: `pytest` or `tox`.
- `execution`: return code, output, timeout state, and whether tests were skipped.

## Configuration

The frontend uses `NEXT_PUBLIC_API_URL` and defaults to `http://localhost:8000`. The backend permits `http://localhost:3000` through CORS.

`backend/.env.example` documents `LLM_API_KEY`; the ignored `backend/.env` holds the local Gemini key. The Docker image must exist locally as `verix-test-runner:dev` and Docker Desktop must be running.

## V0.7 boundaries

- Public GitHub repositories only; no token, private repository, or pull-request integration.
- Python projects only.
- Dependency declarations and test-runner configuration must be at the repository root. Nested monorepository projects are not selected automatically.
- Repository context fetches selected configuration contents, not arbitrary source or test contents.
- Repository execution runs the downloaded default branch only; there is no commit, branch, or subdirectory selection.
- No generated repository tests, coverage measurement, failure investigation, fix proposal, or agent loop.
- No database, Redis, queue, authentication, or background job system.
- Requests are synchronous and one backend process coordinates Docker directly.

## Next evolution

V0.8 will select a bounded set of repository source and existing-test files, use that evidence to generate repository-aware tests, and run generated tests alongside the existing suite. Agentic failure investigation and approved fix proposals remain later milestones.
