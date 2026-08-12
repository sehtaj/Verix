# Verix

Verix is an early-stage AI software quality engineer. Version 0.5 can look up a public GitHub repository's basic metadata and file structure, as well as generate and safely run pytest tests for pasted Python code.

## Requirements

- Python 3
- Node.js 20 or later
- Docker Desktop (running)

## Build the test runner

From the repository root, build the local Docker image used to execute generated tests:

```bash
docker build --tag verix-test-runner:dev backend
```

## Run the backend

From the repository root:

```bash
python3 -m venv backend/.venv
source backend/.venv/bin/activate
pip install -r backend/requirements.txt
cd backend
python3 -m uvicorn main:app --reload
```

The API starts at `http://localhost:8000`.

## Run the frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000` in a browser. Keep both the backend and frontend processes running while using the app.

To point the frontend at a different API address, set `NEXT_PUBLIC_API_URL`; it defaults to `http://localhost:8000`. The backend's local CORS configuration permits requests from `http://localhost:3000`.

## Backend environment variables

`backend/.env.example` documents the Gemini configuration. Do not commit `backend/.env` or an API key.

The Gemini service reads `LLM_API_KEY` from `backend/.env`. If it is missing, `POST /generate` returns HTTP 503. Keep the key private and never expose it to the frontend.

## API

### Health check

`GET /`

```json
{
  "message": "Verix API is running"
}
```

### Generate tests

`POST /generate`

```json
{
  "code": "def add(a, b): return a + b"
}
```

Version 0.5 returns Gemini-generated pytest code and its Docker execution result:

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

An empty `code` value is rejected by the API, and the frontend asks the user to enter code before sending a request. Gemini failures return HTTP 502 with a safe error message.

Generated tests run only inside the local Docker image. The runner has no network access, a read-only container filesystem, restricted resources, and a 10-second timeout. A non-zero `return_code` means the tests failed; a timeout returns `null` for `return_code` and `true` for `timed_out`.

### Fetch repository metadata

`POST /repository`

Accepts a public GitHub repository URL:

```json
{
  "url": "https://github.com/octocat/Hello-World"
}
```

It uses GitHub's public API to return basic repository details. No GitHub token is required, and private repositories are not supported.

```json
{
  "name": "Hello-World",
  "owner": "octocat",
  "description": "My first repository on GitHub!",
  "language": null,
  "stars": 0,
  "url": "https://github.com/octocat/Hello-World"
}
```

The frontend provides a **Fetch repository** action that displays these details. It does not clone, download, inspect, or test repository files yet.

### Fetch repository file structure

`POST /repository/tree`

Accepts the same public GitHub repository URL as `POST /repository`.

```json
{
  "url": "https://github.com/octocat/Hello-World"
}
```

It returns file and directory paths from GitHub's recursive tree API:

```json
{
  "entries": [
    { "path": "README", "type": "blob" },
    { "path": "src", "type": "tree" },
    { "path": "src/app.py", "type": "blob" }
  ],
  "is_truncated": false
}
```

The frontend displays the tree after a repository is selected. Verix shows at most 500 entries and tells you when the result is truncated. GitHub's primary-language value is shown with the repository metadata. This version does not fetch file contents, clone repositories, or execute repository code.
