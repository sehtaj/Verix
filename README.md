# Verix

Verix is an early-stage AI software quality engineer. Version 0.10 can generate and safely execute pytest tests for pasted Python code. For a public Python repository, it can select a branch, tag, or commit; choose a nested project folder and verified source target; preview bounded Gemini context; run original and generated suites separately in Docker; and explain one classified result using bounded evidence.

## Requirements

- Python 3.10 or later.
- Node.js 20.9 or later.
- Docker Desktop, running locally.
- A Gemini API key for pasted-code generation, repository-aware generation, and repository investigation.

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

The API starts at `http://localhost:8000`. The Gemini key is required by `POST /generate`, `POST /repository/generate`, and `POST /repository/investigate`. Repository inspection and `POST /repository/test-run` do not use it.

## 3. Run the frontend

In a second terminal, from the repository root:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`. Keep the frontend, backend, and Docker Desktop running while using Verix.

`NEXT_PUBLIC_API_URL` can point the frontend at a different backend address and defaults to `http://localhost:8000`. The backend's local CORS configuration permits `http://localhost:3000`.

## How to use V0.10

### Inspect and test a repository

1. Enter a canonical public URL such as `https://github.com/owner/repository`.
2. Optionally enter a branch, tag, or full commit SHA. Leave it empty to use the default branch.
3. Optionally enter a repository-relative Python project folder, such as `packages/payments`, for a nested project.
4. Select **Fetch repository** to view metadata, the bounded selected tree, and the test plan. Verix resolves the request to one commit SHA. This inspection does not send source code to Gemini.
5. Keep Verix's automatic source target or choose another verified Python file, then select **Preview Gemini context** to inspect the exact bounded source, test, and configuration content that could be sent to Gemini. Previewing does not call Gemini or run code.
6. Select **Run repository tests**, **Generate repository tests**, or **Investigate repository**. Each action keeps the selected commit, project folder, and target consistent through execution.
7. Review the selected target, generated pytest code, installation status, original/generated results, and—when investigating—the outcome and explanation.

Repository execution supports Python projects with dependency and runner configuration at the repository root. Nested projects in monorepositories are not selected automatically. Dependency installation may download packages in a disposable container. Original and generated tests run afterward without network access and with a read-only repository mount.

Generated tests are temporary and disappear with the disposable workspace. Verix does not commit them to the repository, and LLM-generated tests still require developer judgment.

For repository generation and investigation, Verix resolves the requested reference to one commit SHA and uses that same SHA for the selected context and Docker archive. This prevents a branch update from mixing repository versions within one request. When a project folder is selected, Docker runs from that folder and Gemini receives the project-relative target path needed to choose imports correctly. Gemini receives only bounded execution evidence for investigation and explains the backend's already-selected outcome; it does not retry tests, change code, or propose a patch.

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

Optional request fields are `reference`, `subdirectory`, and `target_path`. This is the inspection endpoint used by the frontend. It resolves the selected reference to one commit SHA and returns:

- Basic repository metadata.
- At most 500 recursive tree entries and an `is_truncated` flag.
- Present allowlisted root configuration files.
- Detected project setup, likely source and test paths, and a structured test plan.
- A `generation_selection` containing one `target_path`, up to three `related_test_paths`, up to three `configuration_paths`, and `is_truncated`.

The response also contains the resolved `revision` and selected `subdirectory`. A selected subdirectory must be a safe repository-relative directory, and a selected target must be a verified Python source file inside it.

The selection contains paths only; source and test contents are not fetched for Gemini until the explicit generation action. GitHub access is unauthenticated, so public API rate limits apply. Private repositories are not supported.

### Preview bounded Gemini context

`POST /repository/context/preview` accepts the same targeting fields, but requires `target_path`. It returns only the exact bounded source, selected existing-test files, configuration files, skipped paths, and total byte count that would be available for repository test generation. It does not call Gemini, install dependencies, or run repository code.

### Prepare and run a repository

`POST /repository/test-run`

```json
{
  "url": "https://github.com/owner/python-repository"
}
```

You may include optional `reference` and `subdirectory` fields. The response separates preparation, installation, and test execution:

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

### Generate and run repository-aware tests

`POST /repository/generate`

```json
{
  "url": "https://github.com/owner/python-repository"
}
```

You may include optional `reference`, `subdirectory`, and `target_path` fields. The response preserves the original and generated outcomes separately:

```json
{
  "target_path": "src/sample.py",
  "generated_tests": "from sample import add\n\ndef test_add(): ...",
  "preparation": {
    "file_count": 24,
    "total_bytes": 18420,
    "skipped_entries": 0
  },
  "installation": {
    "return_code": 0,
    "output": "...",
    "timed_out": false,
    "skipped": false
  },
  "test_runner": "pytest",
  "existing_execution": {
    "return_code": 0,
    "output": "... original tests passed ...",
    "timed_out": false,
    "skipped": false
  },
  "generated_execution": {
    "return_code": 0,
    "output": "... generated tests passed ...",
    "timed_out": false,
    "skipped": false
  }
}
```

Ordinary failing tests return HTTP 200 with a non-zero execution return code. If dependency installation fails, the affected execution is marked as skipped. Invalid or unsupported repository input returns HTTP 422. GitHub, archive, Gemini, invalid generated output, or Docker infrastructure failures return a safe HTTP 502. Missing Gemini configuration returns HTTP 503 for generation endpoints.

### Investigate a repository

`POST /repository/investigate`

```json
{
  "url": "https://github.com/owner/python-repository"
}
```

This endpoint accepts optional `reference`, `subdirectory`, and `target_path` fields. It runs one complete repository investigation and returns the same generated-test execution fields, the test plan, and a small investigation result:

```json
{
  "investigation": {
    "outcome": "existing_tests_failed",
    "explanation": "The existing repository suite reported a failure."
  }
}
```

The possible outcomes are:

- `setup_failed`
- `no_existing_tests`
- `existing_tests_timed_out`
- `existing_tests_failed`
- `generated_tests_timed_out`
- `generated_tests_failed`
- `tests_passed`

The outcome is selected by fixed backend rules. Gemini receives bounded command evidence only to explain that outcome. A normal test failure or no-existing-tests result returns HTTP 200; invalid input returns HTTP 422; external, validation, or Docker failures return HTTP 502; and a missing Gemini key returns HTTP 503.

The focused repository endpoints remain available for development and inspection:

- `POST /repository`
- `POST /repository/tree`
- `POST /repository/configuration`
- `POST /repository/paths`
- `POST /repository/setup`
- `POST /repository/test-plan`

Each accepts the same repository URL object. The frontend uses `/repository/context` because it avoids repeating metadata and tree requests.

## Execution safety and limits

Generation context is intentionally focused:

- One automatically selected Python source target.
- Up to three related test files and three configuration files.
- 64 KiB maximum per selected context file.
- 128 KiB maximum total generation context.
- 128 KiB maximum generated pytest module.
- UTF-8, non-empty, NUL-free, valid Python generated output.
- One reserved temporary path: `.verix-generated-tests/test_verix_generated.py`.
- No overwrite of repository files.

Repository archives are limited to 25 MiB compressed, 100 MiB extracted regular-file content, and 10,000 entries. Unsafe paths are rejected; links and special entries are skipped; temporary workspaces are removed after each request.

Repository dependency installation uses fixed backend-selected commands in a disposable container with one CPU, 512 MiB memory, 128 processes, and a 180-second timeout per step. It has network access and a writable temporary repository copy because package installation requires both. Tox environments and their dependencies are prepared during this stage. Package build scripts are untrusted code running inside this bounded container.

Original and generated repository tests run separately with no network, a read-only repository mount, the same CPU/memory/process bounds, and a 60-second timeout per container command. For generated tests, tox repositories first use a separate bounded environment-discovery command, then reuse only one prepared default environment, preferring a Python-style name such as `py313` and otherwise using the first valid default. This avoids running the generated pytest command across every configured lint or documentation environment. Returned output is capped at 50,000 characters. Pasted-code tests use stricter 256 MiB memory, 64-process, and 10-second limits.

Repository investigation evidence includes at most 2,000 characters each from dependency installation, the existing suite, and the generated suite. Gemini's explanation is capped at 4,000 characters. The investigation still runs synchronously and does not retry commands or modify repository files.

Docker isolation reduces risk but is not a complete multi-tenant security boundary. V0.9 is intended for local development with the local Docker daemon treated as trusted infrastructure.

## Quick verification

With the backend running:

```bash
curl http://localhost:8000/
```

Run the deterministic backend checks from the repository root:

```bash
python3 -m unittest discover -s backend/tests -v
python3 -m compileall backend
```

Check the production frontend build:

```bash
cd frontend
npm run build
```

For an end-to-end V0.10 check, use a small public Python repository with a nested project folder, select its branch or commit, folder, and target, preview the context, then select **Investigate repository**. Verify the resolved commit, previewed content, outcome, explanation, generated code, and separate original/generated panels. During the V0.10 review, `https://github.com/sehtaj/competitive-programming` with reference `main`, subdirectory `python/arraysAndHashing`, and target `python/arraysAndHashing/duplicate_integers.py` reported `no_existing_tests` (pytest exit code 5), while the generated suite passed.

## V0.10 boundaries

V0.10 supports public Python repositories, one validated branch/tag/full-commit reference, one validated project subdirectory, and one verified Python source target. It does not support private repositories, authenticated GitHub access, arbitrary local filesystem paths, multiple targets, coverage, fix proposals, automatic retries, patch application, or a multi-step agent loop. Generated tests are not committed back and are not guaranteed to be logically correct. Investigation explanations are evidence-grounded summaries, not guaranteed root-cause diagnoses.

The selected target must come from the commit-pinned tree and remain inside the selected project directory. This prevents a user-supplied path from escaping the disposable Docker workspace.
