# Verix Architecture

## Purpose

Verix is a small client-server application. Version 0.1 proves the user flow for submitting Python code to a backend and displaying a structured placeholder result. It does not generate or execute tests.

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
  | validates code and returns placeholder data
  v
Next.js displays { "tests": "Coming soon" }
```

The frontend is responsible for the interface and API request state. The backend is responsible for API validation and responses. No user code is executed.

## Repository structure

```text
verix/
├── backend/
│   ├── main.py
│   ├── services/
│   │   └── llm_service.py
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
- Exposes the health and placeholder generate endpoints.

`backend/services/llm_service.py` contains the Gemini integration. It loads the local API key, sends a Python function to Gemini, and returns generated pytest code. The endpoint does not call this service yet; that is the next V0.2 task.

Separate `models`, `routes`, and backend test folders are not present yet. They should be introduced only when the current files become difficult to maintain.

### Frontend

`frontend/app/page.tsx` is a client component containing the complete V0.1 interface:

- A controlled textarea for pasted Python code.
- Empty-input validation.
- A `POST /generate` request to `NEXT_PUBLIC_API_URL`, defaulting to `http://localhost:8000`.
- Loading, error, and result states.

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

V0.1 response:

```json
{
  "tests": "Coming soon"
}
```

An empty `code` value is rejected with FastAPI's validation response. The frontend also prevents empty submissions before sending a request.

## Configuration

The frontend supports `NEXT_PUBLIC_API_URL` for its backend address and defaults to `http://localhost:8000`.

`backend/.env.example` documents `LLM_API_KEY`, which the Gemini service reads from an ignored `backend/.env` file. The key is never sent to the frontend.

## V0.1 boundaries

The following are deliberately outside the current architecture:

- LLM calls from the `/generate` endpoint
- Test execution
- Docker or any code execution
- Databases, Redis, queues, authentication, and background jobs
- Repository analysis and GitHub integration

## Next evolution

The next V0.2 task connects the existing `/generate` endpoint to the Gemini service. The request and response flow can remain the same while the placeholder result is replaced with generated tests. Docker execution remains a later version because untrusted code must not run on the host.
