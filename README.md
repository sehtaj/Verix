# Verix

Verix is an early-stage AI software quality engineer. Version 0.1 accepts a pasted Python function and returns a placeholder unit-test result.

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

Open `http://localhost:3000` in a browser.

To point the frontend at a different API address, set `NEXT_PUBLIC_API_URL`; it defaults to `http://localhost:8000`.

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

Version 0.1 returns a placeholder response:

```json
{
  "tests": "Coming soon"
}
```
