# Verix

Verix is an early-stage AI software quality engineer. Version 0.2 accepts pasted Python code and uses Gemini to generate pytest test code. It does not execute generated tests.

## Requirements

- Python 3
- Node.js 20 or later

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

`backend/.env.example` lists backend configuration reserved for future features. Do not commit `backend/.env` or an API key.

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

Version 0.2 returns Gemini-generated pytest code:

```json
{
  "tests": "import pytest\n\ndef test_add(): ..."
}
```

An empty `code` value is rejected by the API, and the frontend asks the user to enter code before sending a request. Gemini failures return HTTP 502 with a safe error message.
