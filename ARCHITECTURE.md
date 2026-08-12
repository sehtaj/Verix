# Verix Architecture

## Purpose

Verix is a small client-server application. Version 0.5 can look up basic metadata and a bounded file tree for public GitHub repositories, in addition to generating and executing pytest tests for submitted Python code.

## Current architecture

```text
Browser
  |
  v
Next.js frontend (localhost:3000)
  |                               |
  | POST /repository             | POST /generate
  | POST /repository/tree         v
  v                           Gemini API
FastAPI repository service         |
  |                                 | generated pytest code
  | GET metadata + recursive tree  v
  v                           Docker pytest runner
GitHub public API                  |
  |                                 | execution result
  | repository details + paths     v
  v                           Next.js displays test results
Next.js displays repository metadata and file structure
```

The frontend is responsible for the interface and API request state. The backend validates repository URLs, retrieves public metadata and paths, calls Gemini, and coordinates test execution. User code and generated tests are never executed on the host.

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

- Creates the FastAPI application.
- Permits browser requests from `http://localhost:3000` with CORS.
- Defines the Pydantic request model for `/generate`.
- Exposes the health and Gemini-backed generate endpoints.
- Returns HTTP 503 when the local LLM configuration is unavailable and HTTP 502 when Gemini generation fails.
- Runs generated tests with `DockerTestRunner` and returns their execution details.
- Exposes `POST /repository` for public GitHub repository metadata.
- Exposes `POST /repository/tree` for a bounded public GitHub repository tree.

`backend/services/llm_service.py` contains the Gemini integration. It loads the local API key, sends submitted Python code to Gemini, and returns pytest code that imports the submitted symbols from `main`.

`backend/services/github_service.py` validates canonical public GitHub URLs and calls GitHub's unauthenticated metadata and recursive-tree endpoints. It returns basic metadata plus up to 500 file or directory paths, marking the response when GitHub or Verix truncates it. It does not clone repositories or retrieve file contents. `certifi` supplies the CA bundle for the outbound HTTPS connection.

`backend/services/test_runner.py` writes submitted code to `main.py` and generated tests to `test_generated.py` in a temporary workspace, then invokes the local `verix-test-runner:dev` image. The runner container has no network access, a read-only filesystem and workspace mount, no Linux capabilities, no new privileges, PID and memory limits, a temporary `/tmp`, and a 10-second host-side timeout. The timeout path removes the named container before returning a timeout result.

`backend/Dockerfile` provides the small runner image: Python, pytest, and a non-root `runner` user.

Separate `models`, `routes`, and backend test folders are not present yet. They should be introduced only when the current files become difficult to maintain.

### Frontend

`frontend/app/page.tsx` is a client component containing the complete V0.5 interface:

- A separate form that validates a public GitHub repository URL and fetches its metadata and file tree.
- An indented, scrollable tree that shows paths and distinguishes directories from files.
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

### `POST /repository`

Accepts a public GitHub repository URL.

```json
{
  "url": "https://github.com/octocat/Hello-World"
}
```

It returns the repository owner, name, description, primary language, star count, and canonical GitHub URL. Invalid, private, or unavailable repositories receive a safe error response. No GitHub token is used.

### `POST /repository/tree`

Accepts the same public GitHub repository URL as `POST /repository` and returns a recursive list of file and directory paths.

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

## Configuration

The frontend supports `NEXT_PUBLIC_API_URL` for its backend address and defaults to `http://localhost:8000`.

`backend/.env.example` documents `LLM_API_KEY`, which the Gemini service reads from an ignored `backend/.env` file. The key is never sent to the frontend. The Docker runner image must be built locally as `verix-test-runner:dev` before test generation can execute. Repository metadata uses GitHub's public API and does not need a token.

## V0.5 boundaries

The following are deliberately outside the current architecture:

- Databases, Redis, queues, authentication, and background jobs
- Repository cloning, file-content retrieval, and test generation from repositories
- Private repositories and GitHub authentication
- Repository analysis agents
- Automatic bug explanations or fixes

## Next evolution

V0.6 will retrieve focused repository context, identify likely source and test paths, and produce a structured testing plan. The first multi-step agent workflow comes later, after Verix can understand repository context and execute its existing tests reliably. User-provided and AI-generated code must continue to run only inside isolated containers.
