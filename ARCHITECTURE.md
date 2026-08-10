# Verix Architecture

## Purpose

Verix is a small client-server application. Version 0.3 generates pytest test code from submitted Python code with Gemini, then executes it in an isolated local Docker container.

## Current architecture

```text
Browser
  |
  v
Next.js frontend (localhost:3000)
  |
  | POST /generate { "code": "..." }
  v
FastAPI backend (localhost:8000)
  |
  | validates code and asks Gemini for pytest tests
  v
Gemini API
  |
  | returns generated pytest code
  v
FastAPI test runner service
  |
  | mounts code and tests read-only
  v
Docker pytest runner
  |
  | returns exit code, output, and timeout status
  v
Next.js displays tests and execution results
```

The frontend is responsible for the interface and API request state. The backend is responsible for validation, Gemini calls, and coordinating test execution. User code and generated tests are never executed on the host.

## Repository structure

```text
verix/
├── backend/
│   ├── Dockerfile
│   ├── main.py
│   ├── services/
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

- Creates the FastAPI application.
- Permits browser requests from `http://localhost:3000` with CORS.
- Defines the Pydantic request model for `/generate`.
- Exposes the health and Gemini-backed generate endpoints.
- Returns HTTP 503 when the local LLM configuration is unavailable and HTTP 502 when Gemini generation fails.
- Runs generated tests with `DockerTestRunner` and returns their execution details.

`backend/services/llm_service.py` contains the Gemini integration. It loads the local API key, sends submitted Python code to Gemini, and returns pytest code that imports the submitted symbols from `main`.

`backend/services/test_runner.py` writes submitted code to `main.py` and generated tests to `test_generated.py` in a temporary workspace, then invokes the local `verix-test-runner:dev` image. The runner container has no network access, a read-only filesystem and workspace mount, no Linux capabilities, no new privileges, PID and memory limits, a temporary `/tmp`, and a 10-second host-side timeout. The timeout path removes the named container before returning a timeout result.

`backend/Dockerfile` provides the small runner image: Python, pytest, and a non-root `runner` user.

Separate `models`, `routes`, and backend test folders are not present yet. They should be introduced only when the current files become difficult to maintain.

### Frontend

`frontend/app/page.tsx` is a client component containing the complete V0.3 interface:

- A controlled textarea for pasted Python code.
- Empty-input validation.
- A `POST /generate` request to `NEXT_PUBLIC_API_URL`, defaulting to `http://localhost:8000`.
- Loading, error, generated-test, and execution-result states.

`frontend/app/globals.css` supplies the small amount of plain CSS used by the page. There are no reusable components or frontend helper modules yet because the UI has one page and no duplicated behavior.

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

V0.3 response:

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

An empty `code` value is rejected with FastAPI's validation response. The frontend also prevents empty submissions before sending a request. Gemini failures return HTTP 502 with a safe error message; a missing key returns HTTP 503. Test failures return normally with a non-zero `execution.return_code`; timeouts return `null` for the return code and `true` for `execution.timed_out`.

## Configuration

The frontend supports `NEXT_PUBLIC_API_URL` for its backend address and defaults to `http://localhost:8000`.

`backend/.env.example` documents `LLM_API_KEY`, which the Gemini service reads from an ignored `backend/.env` file. The key is never sent to the frontend. The Docker runner image must be built locally as `verix-test-runner:dev` before test generation can execute.

## V0.3 boundaries

The following are deliberately outside the current architecture:

- Databases, Redis, queues, authentication, and background jobs
- Repository analysis and GitHub integration
- Automatic bug explanations or fixes

## Next evolution

V0.4 will begin accepting GitHub repositories. User-provided and AI-generated code must continue to run only inside isolated containers.
