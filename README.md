# Verix

Verix is an early-stage AI software quality engineer. Version 0.7 can generate and safely execute pytest tests for pasted Python code. It can also inspect a public GitHub repository, explain its likely test setup, prepare a bounded Python repository archive, install supported dependencies, and run the repository's existing pytest or tox suite in Docker.

## Requirements

- Python 3.10 or later
- Node.js 20 or later
- Docker Desktop, running locally
- A Gemini API key for pasted-code test generation

## 1. Build the runner image

From the repository root:

```bash
docker build --tag verix-test-runner:dev backend
```

The image contains Python, pytest, tox, and a non-root execution user. Rebuild it after changing `backend/Dockerfile`.

## 2. Configure and run the backend

Create a local environment file from the example and add your Gemini key. Never commit this file or the key.

```bash
cp backend/.env.example backend/.env
```

The file should contain:

```dotenv
LLM_API_KEY=your_gemini_api_key
```

Create the Python environment, install the backend dependencies, and start FastAPI:

```bash
python3 -m venv backend/.venv
source backend/.venv/bin/activate
pip install -r backend/requirements.txt
cd backend
python3 -m uvicorn main:app --reload
```

The API starts at `http://localhost:8000`. The Gemini key is required only for `POST /generate`; repository inspection and execution do not use it.

## 3. Run the frontend

In a second terminal, from the repository root:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`. Keep the frontend, backend, and Docker Desktop running while using Verix.

`NEXT_PUBLIC_API_URL` can point the frontend at a different backend address and defaults to `http://localhost:8000`. The backend's local CORS configuration permits `http://localhost:3000`.

## How to use V0.7

### Inspect and test a repository

1. Enter a canonical public URL such as `https://github.com/owner/repository`.
2. Select **Fetch repository** to view metadata, a bounded file tree, and the evidence-based test plan.
3. Select **Run repository tests** to explicitly download and prepare the default branch, install supported dependencies, and run its existing test suite.
4. Review the preparation metrics, installation status, selected runner, exit code, and output.

Repository execution currently supports Python projects with dependency and runner configuration at the repository root. Nested Python projects in monorepositories are not selected automatically. Dependency installation may download packages in a disposable container. The subsequent pytest or tox run has no network access and a read-only repository mount.

### Generate tests for pasted code

Paste Python code and select **Generate tests**. Gemini creates pytest source, and Verix executes the submitted code and generated tests inside its local Docker runner. The page displays both the generated tests and the result.

## API

### Health check

`GET /`

```json
{
  "message": "Verix API is running"
}
```

### Generate and run pasted-code tests

`POST /generate`

```json
{
  "code": "def add(a, b): return a + b"
}
```

Successful generation returns the pytest source and Docker execution result:

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

An empty code value is rejected. A missing key returns HTTP 503, and a Gemini failure returns HTTP 502. Test failures are returned normally with a non-zero `return_code`.

### Fetch consolidated repository context

`POST /repository/context`

```json
{
  "url": "https://github.com/owner/repository"
}
```

This is the inspection endpoint used by the frontend. It fetches shared GitHub evidence once and returns:

- Basic repository metadata.
- At most 500 recursive tree entries and an `is_truncated` flag.
- Present allowlisted root configuration files.
- Detected project setup, likely source and test paths, and a structured test plan.

GitHub access is unauthenticated, so public API rate limits apply. Private repositories are not supported.

### Prepare and run a repository

`POST /repository/test-run`

```json
{
  "url": "https://github.com/owner/python-repository"
}
```

The response separates preparation, installation, and test execution:

```json
{
  "preparation": {
    "file_count": 24,
    "total_bytes": 18420,
    "skipped_entries": 0
  },
  "installation": {
    "return_code": 0,
    "output": "No supported dependency declaration was found; installation was skipped.\n",
    "timed_out": false,
    "skipped": true
  },
  "test_runner": "pytest",
  "execution": {
    "return_code": 0,
    "output": "... 3 passed ...",
    "timed_out": false,
    "skipped": false
  }
}
```

A failing test suite still returns HTTP 200 with a non-zero execution return code. If dependency installation fails, execution is marked as skipped. Invalid or unsupported repositories return HTTP 422. GitHub, archive, or Docker orchestration failures return a safe HTTP 502 response.

The focused repository endpoints remain available for development and inspection:

- `POST /repository`
- `POST /repository/tree`
- `POST /repository/configuration`
- `POST /repository/paths`
- `POST /repository/setup`
- `POST /repository/test-plan`

Each accepts the same repository URL object. The frontend uses `/repository/context` because it avoids repeating metadata and tree requests.

## Execution safety and limits

Repository archives are limited to 25 MiB compressed, 100 MiB extracted regular-file content, and 10,000 entries. Unsafe paths are rejected; links and special entries are skipped; temporary workspaces are removed after each request.

Repository dependency installation uses fixed backend-selected commands in a disposable container with one CPU, 512 MiB memory, 128 processes, and a 180-second timeout per step. It has network access and a writable temporary repository copy because package installation requires both. Tox environments and their declared dependencies are prepared during this stage and reused without another installation step during testing. Package build scripts are therefore untrusted code running inside this bounded container.

Repository tests run in a separate container with no network, a read-only repository mount, the same CPU/memory/process bounds, and a 60-second timeout. Returned output is capped at 50,000 characters. Pasted-code tests use stricter 256 MiB memory, 64-process, and 10-second limits.

Docker isolation reduces risk but is not a complete multi-tenant security boundary. V0.7 is intended for local development with the local Docker daemon treated as trusted infrastructure.

## Quick verification

With the backend running:

```bash
curl http://localhost:8000/
```

Check the production frontend build:

```bash
cd frontend
npm run build
```

Check Python syntax from the repository root:

```bash
python3 -m compileall backend
```

For an end-to-end check, use a small public Python repository with a root-level `requirements.txt`, `pyproject.toml`, `setup.py`, or `tox.ini`, then run it through both repository buttons in the browser.

## V0.7 boundaries

V0.7 does not generate tests from repository source, calculate coverage, investigate failures, propose patches, access private repositories, select nested projects, or run an agent loop. Those capabilities belong to later versions.
