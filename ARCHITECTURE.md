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
│   ├── requirements.txt
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

`backend/main.py` contains the entire V0.1 FastAPI application because the API is small:

- Creates the FastAPI application.
- Permits browser requests from `http://localhost:3000` with CORS.
- Defines the Pydantic request model for `/generate`.
- Exposes the health and generate endpoints.

Separate `models`, `routes`, `services`, and backend test folders are not present yet. They should be introduced only when the single module becomes difficult to maintain.

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

`backend/.env.example` reserves `LLM_API_KEY` for the V0.2 LLM service. Real values belong in an ignored `backend/.env` file or in the process environment; the key is not read or required until that service is implemented.

## V0.1 boundaries

The following are deliberately outside the current architecture:

- LLM providers and API-key use
- Test generation beyond the placeholder response
- Docker or any code execution
- Databases, Redis, queues, authentication, and background jobs
- Repository analysis and GitHub integration

## Next evolution

V0.2 may add an LLM service behind the existing `/generate` endpoint. The request and response flow can remain the same while the placeholder result is replaced with generated tests. Docker execution remains a later version because untrusted code must not run on the host.
