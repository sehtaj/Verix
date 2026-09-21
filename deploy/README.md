# Hosted Verix demo

The approved no-card deployment shape is:

```text
Vercel Next.js frontend
        |
Render free FastAPI backend (one worker, one admitted execution)
        |
E2B disposable cloud sandbox (public repository dependencies and tests)
```

Docker remains the default local execution backend. Hosted execution selects
E2B with `VERIX_EXECUTION_BACKEND=e2b`; application workflows depend on one
runner contract rather than either provider.

## Why E2B is separate

Render coordinates requests and holds the backend-only Gemini and E2B keys. It
does not execute repository, dependency-build, generated-test, or patched code.
Each execution uses a short-lived E2B sandbox. Dependency installation starts
with network access; before pytest or tox starts, Verix atomically denies all
outbound IPv4 and IPv6 traffic for the rest of that sandbox. The sandbox is
killed when the workflow exits, including exceptional exits.

## 1. E2B account and runner template

Create an E2B Hobby account, create one API key, and place it only in the local
`backend/.env` while preparing deployment:

```dotenv
E2B_API_KEY=replace-with-e2b-key
E2B_TEMPLATE=verix-python-runner
```

Build the reviewed runner template once from the repository root:

```bash
backend/.venv/bin/python backend/scripts/build_e2b_template.py
```

The template contains Python, pytest, tox, coverage.py, the trusted Verix
coverage entrypoint, and an unprivileged `runner` user. It contains no Gemini,
GitHub, E2B, or other application credential.

## 2. Render backend

Create a Render Blueprint from the root `render.yaml`. It defines one free
Python web service, one Uvicorn worker, exact public-demo ceilings, and three
secret values that Render must request rather than read from Git:

- `E2B_API_KEY`: the E2B key created above;
- `LLM_API_KEY`: the configured model-provider key;
- `VERIX_CORS_ORIGINS`: the exact Vercel production origin, without a trailing
  slash.

Render free services sleep after 15 idle minutes, so the first request can take
about one minute. If the free monthly allowance is exhausted and no payment
method exists, Render suspends the service instead of billing it.

## 3. Vercel frontend

Create a Vercel project with `frontend` as its root directory and set:

```dotenv
NEXT_PUBLIC_API_URL=https://replace-with-render-service.onrender.com
```

Deploy the reviewed Git revision. Copy the final Vercel origin into Render's
`VERIX_CORS_ORIGINS`, then redeploy the backend so its exact-origin policy is
active.

## 4. Acceptance checks

Before sharing the site:

1. Verify the Render `/` health response and the Vercel production page.
2. Run every deterministic verification example through E2B.
3. Verify dependency installation can access package registries but tests run
   after the network-deny update.
4. Verify the E2B sandbox is killed after success, failure, and timeout.
5. Verify only one expensive request is admitted at a time.
6. Confirm secrets are present only in provider settings or ignored local env
   files, never Git or the E2B sandbox environment.
7. Complete the configured-model benchmark before describing the release as
   ready for public use.

E2B's no-card Hobby allowance is finite. Verix's one-job ceiling, command
timeouts, sandbox lifetime, request rate, and daily LLM limit reduce accidental
usage, but the demo must stop safely when provider credits are exhausted.
