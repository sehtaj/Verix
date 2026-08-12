# Verix Architecture

## Purpose

Verix is a small client-server application. Version 0.6 can generate and safely run pytest tests for pasted Python code, and can build an evidence-based test plan for a selected public GitHub repository.

## Current architecture

```text
Browser
  |
  v
Next.js frontend (localhost:3000)
  |                                      |
  | POST /repository                     | POST /generate
  | POST /repository/tree                v
  | POST /repository/test-plan       Gemini API
  v                                      |
FastAPI repository service                | generated pytest code
  |                                      v
  | GET metadata, recursive tree,    Docker pytest runner
  | and selected configuration files      |
  v                                      | execution result
GitHub public API                          v
  |                                  Next.js displays test results
  | repository evidence
  v
Repository metadata, file tree, and test plan displayed in Next.js
```

The frontend owns interface state and rendering. The backend validates public GitHub URLs, retrieves repository evidence, derives a test plan, calls Gemini for pasted code, and coordinates isolated test execution. User code and Gemini-generated tests are never executed on the host.

## Repository structure

```text
verix/
├── backend/
│   ├── Dockerfile
│   ├── main.py
│   ├── services/
│   │   ├── github_service.py
│   │   ├── llm_service.py
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

### Backend

`backend/main.py` contains the FastAPI application because the API is still small:

- Creates the FastAPI application and permits `http://localhost:3000` through CORS.
- Defines Pydantic request models for pasted code and repository URLs.
- Exposes `GET /`, the Gemini-backed `POST /generate`, and the repository endpoints.
- Runs generated pasted-code tests with `DockerTestRunner` and returns their execution details.
- Converts invalid repository requests to HTTP 422 and upstream GitHub failures to safe HTTP 502 responses.

`backend/services/github_service.py` validates canonical public GitHub URLs and calls GitHub's unauthenticated API. It retrieves metadata, a recursive tree limited to 500 displayed entries, and only these root-level configuration files when present: `pyproject.toml`, `requirements.txt`, `setup.cfg`, `setup.py`, `Pipfile`, and `tox.ini`.

The service derives likely Python source and test paths from naming conventions, recognizes common project tools (Poetry, PDM, Hatch, Pipenv, setuptools, and pip) and test runners (pytest and tox), then constructs a plan from that evidence. The plan makes no claim that its inferred paths are complete when the tree is truncated. `certifi` supplies the CA bundle for outbound HTTPS.

`backend/services/llm_service.py` loads the local API key, sends pasted Python code to Gemini, and returns pytest code that imports submitted symbols from `main`.

`backend/services/test_runner.py` writes pasted code to `main.py` and generated tests to `test_generated.py` in a temporary workspace, then invokes the local `verix-test-runner:dev` image. The runner container has no network access, a read-only filesystem and workspace mount, no Linux capabilities, no new privileges, PID and memory limits, a temporary `/tmp`, and a 10-second host-side timeout. The timeout path removes the named container before returning a timeout result.

`backend/Dockerfile` provides the small runner image: Python, pytest, and a non-root `runner` user.

Separate models, routes, and backend test folders are not present yet. They should be introduced only when the current files become difficult to maintain.

### Frontend

`frontend/app/page.tsx` is a client component containing the complete V0.6 interface:

- A form that validates a public GitHub repository URL and retrieves its metadata, tree, and test plan.
- A scrollable, indented file tree with an incomplete-result indication.
- A repository test-plan summary showing detected setup, likely source/test counts, suggested commands, and warnings.
- A controlled textarea for pasted Python code with validation, loading, error, generated-test, and execution-result states.
- Requests to `NEXT_PUBLIC_API_URL`, defaulting to `http://localhost:8000`.

`frontend/app/globals.css` supplies the plain CSS for the single page. There are no reusable components or frontend helper modules yet because the UI has one page and no duplicated behavior.

## API contract

### `GET /`

Confirms that the backend is running.

```json
{
  "message": "Verix API is running"
}
```

### `POST /generate`

Accepts a non-empty code string.

```json
{
  "code": "def add(a, b): return a + b"
}
```

It returns Gemini-generated pytest code and its Docker execution result:

```json
{
  "tests": "from main import add\n\ndef test_add(): ...",
  "execution": {
    "return_code": 0,
    "output": "... 1 passed ...",
    "timed_out": false
  }
}
```

An empty `code` value is rejected with FastAPI's validation response. Gemini failures return HTTP 502 and a missing key returns HTTP 503. Test failures return normally with a non-zero `execution.return_code`; timeouts return `null` for the return code and `true` for `execution.timed_out`.

### `POST /repository`

Accepts a public GitHub repository URL and returns the owner, name, description, primary language, star count, and canonical GitHub URL.

### `POST /repository/tree`

Accepts the same repository URL and returns a recursive list of file and directory paths.

```json
{
  "entries": [
    { "path": "src", "type": "tree" },
    { "path": "src/app.py", "type": "blob" }
  ],
  "is_truncated": false
}
```

The endpoint returns at most 500 entries. `is_truncated` is `true` when the displayed result is incomplete.

### `POST /repository/configuration`

Returns selected root-level Python configuration files and their decoded text.

```json
{
  "files": [
    { "path": "pyproject.toml", "content": "[project]\nname = \"example\"" }
  ]
}
```

### `POST /repository/paths`

Returns likely Python source and test paths inferred from the bounded tree.

```json
{
  "source_paths": ["src/example/app.py"],
  "test_paths": ["tests/test_app.py"],
  "is_truncated": false
}
```

### `POST /repository/setup`

Returns recognized Python tooling and test-runner information based on selected configuration files.

```json
{
  "is_python_project": true,
  "project_tool": "poetry",
  "test_runner": "pytest",
  "configuration_files": ["pyproject.toml"]
}
```

### `POST /repository/test-plan`

Combines the selected configuration and inferred paths into an evidence-based plan.

```json
{
  "setup": {
    "is_python_project": true,
    "project_tool": "poetry",
    "test_runner": "pytest",
    "configuration_files": ["pyproject.toml"]
  },
  "source_paths": ["src/example/app.py"],
  "test_paths": ["tests/test_app.py"],
  "steps": [
    {
      "action": "prepare_environment",
      "description": "Prepare dependencies with poetry.",
      "command": "poetry install"
    }
  ],
  "is_truncated": false
}
```

## Configuration

The frontend supports `NEXT_PUBLIC_API_URL` for its backend address and defaults to `http://localhost:8000`.

`backend/.env.example` documents `LLM_API_KEY`, which the Gemini service reads from an ignored `backend/.env` file. The key is never sent to the frontend. The Docker runner image must be built locally as `verix-test-runner:dev` before pasted-code test generation can execute.

Repository information uses GitHub's public unauthenticated API. No token is required, but GitHub rate limits apply.

## V0.6 boundaries

The following are deliberately outside the current architecture:

- Databases, Redis, queues, authentication, and background jobs
- Arbitrary repository source/test-file retrieval and repository cloning
- Dependency installation or repository test execution
- Private repositories and GitHub authentication
- Repository analysis agents
- Automatic bug explanations or fixes

## Next evolution

V0.7 will consolidate repository-context requests, then prepare and execute existing tests from public Python repositories in an isolated environment. The agentic investigation loop comes later, after Verix can gather context and execute repository tests reliably. User-provided and AI-generated code must continue to run only inside isolated containers.
