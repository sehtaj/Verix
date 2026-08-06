# Verix Architecture

## 1. Purpose

This document explains how Verix is structured, how its components communicate, and where different responsibilities belong.

Verix should begin with the simplest architecture that supports Version 0.1 while remaining easy to extend later.

The project should not use microservices, agent frameworks, databases, queues, or other infrastructure until a real feature requires them.

---

## 2. Current Architecture

Verix currently uses a simple client-server architecture.

```text
User
  |
  v
Next.js Frontend
  |
  | HTTP request
  v
FastAPI Backend
  |
  | Process request
  v
Response returned to Frontend
```

For Version 0.1:

```text
User pastes Python code
          |
          v
Frontend sends POST /generate
          |
          v
FastAPI validates the request
          |
          v
Backend returns placeholder tests
          |
          v
Frontend displays the response
```

---

## 3. Repository Structure

```text
verix/
├── frontend/
├── backend/
├── PROJECT.md
├── ARCHITECTURE.md
├── TODO.md
├── README.md
└── .gitignore
```

### `frontend/`

Contains the Next.js application.

Responsibilities:

- Display the user interface
- Accept code from the user
- Send requests to the backend
- Show loading, success, and error states
- Display generated tests and reports

The frontend must not:

- Store secret API keys
- Call LLM providers directly
- Execute user code
- Control Docker containers
- Contain backend business logic

---

### `backend/`

Contains the FastAPI application.

Responsibilities:

- Receive requests from the frontend
- Validate request data
- Generate tests
- Call external LLM APIs
- Execute tests safely in future versions
- Analyze test results
- Return structured responses
- Protect secret keys and server configuration

The backend is the main application logic layer.

---

## 4. Frontend Architecture

The frontend uses:

- Next.js
- React
- TypeScript
- Tailwind CSS

Initial structure:

```text
frontend/
├── app/
│   ├── page.tsx
│   ├── layout.tsx
│   └── globals.css
├── components/
├── lib/
├── public/
├── package.json
└── tsconfig.json
```

### `app/`

Contains pages, layouts, and routes.

For Version 0.1, `app/page.tsx` contains the main interface.

### `components/`

Contains reusable UI components.

Possible future components:

```text
components/
├── CodeInput.tsx
├── GenerateButton.tsx
├── TestOutput.tsx
└── ErrorMessage.tsx
```

Do not split components unnecessarily. Create a component only when it improves readability or reuse.

### `lib/`

Contains frontend helper functions.

Example:

```text
lib/
└── api.ts
```

`api.ts` may contain the function responsible for calling the FastAPI backend.

---

## 5. Backend Architecture

The backend uses:

- Python
- FastAPI
- Pydantic
- Uvicorn

Initial structure:

```text
backend/
├── main.py
├── models/
├── routes/
├── services/
├── tests/
└── requirements.txt
```

For the first implementation, the backend may begin with only:

```text
backend/
├── main.py
└── requirements.txt
```

Additional folders should be introduced only when `main.py` becomes difficult to maintain.

---

### `main.py`

The application entry point.

Responsibilities:

- Create the FastAPI application
- Configure basic application settings
- Register API routes
- Configure CORS when required
- Expose health-check endpoints

Business logic should gradually move out of `main.py` as the project grows.

---

### `models/`

Contains Pydantic request and response models.

Example:

```text
models/
├── request.py
└── response.py
```

Possible models:

```python
class GenerateTestsRequest(BaseModel):
    code: str
```

```python
class GenerateTestsResponse(BaseModel):
    tests: str
```

Models define the structure of data entering and leaving the backend.

---

### `routes/`

Contains API endpoint definitions.

Example:

```text
routes/
└── generate.py
```

Routes should:

- Receive requests
- Call the appropriate service
- Return responses
- Handle HTTP-related errors

Routes should not contain large amounts of business logic.

---

### `services/`

Contains the main application logic.

Future examples:

```text
services/
├── test_generator.py
├── llm_service.py
├── docker_runner.py
└── report_generator.py
```

A service should perform one clear job.

For example:

- `llm_service.py` communicates with an LLM provider.
- `test_generator.py` creates prompts and processes generated tests.
- `docker_runner.py` runs code inside isolated containers.
- `report_generator.py` creates structured verification reports.

---

### `tests/`

Contains tests for the Verix backend itself.

This is different from the tests that Verix generates for user code.

Example:

```text
tests/
├── test_generate_route.py
└── test_test_generator.py
```

Verix must test its own behavior before it can reliably test other projects.

---

## 6. API Design

### Health Check

```http
GET /
```

Example response:

```json
{
  "message": "Verix API is running"
}
```

---

### Generate Tests

```http
POST /generate
```

Request:

```json
{
  "code": "def add(a, b): return a + b"
}
```

Version 0.1 response:

```json
{
  "tests": "Coming soon"
}
```

Future response:

```json
{
  "language": "python",
  "framework": "pytest",
  "tests": "def test_add():\n    assert add(1, 2) == 3",
  "warnings": [],
  "metadata": {
    "generated_test_count": 1
  }
}
```

The response should remain structured and predictable.

---

## 7. Communication Between Frontend and Backend

The frontend communicates with the backend using HTTP and JSON.

Example:

```text
Next.js
   |
   | POST http://localhost:8000/generate
   |
   | {
   |   "code": "..."
   | }
   v
FastAPI
   |
   | {
   |   "tests": "..."
   | }
   v
Next.js
```

The frontend should not depend on internal backend implementation details.

It should only depend on the API contract.

---

## 8. Environment Variables

Secret or environment-specific values must not be hardcoded.

Backend example:

```env
LLM_API_KEY=
FRONTEND_URL=http://localhost:3000
```

Frontend example:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Important:

Variables beginning with `NEXT_PUBLIC_` are visible in the browser.

Secret keys must never use that prefix and must never be stored in the frontend.

---

## 9. Security Boundary

The backend is the security boundary of Verix.

```text
Browser
   |
   v
Frontend
   |
   v
FastAPI Backend
   |
   v
Disposable Docker Container
```

The browser must never directly access:

- LLM API keys
- Docker
- Host system files
- Uploaded repository contents outside approved operations
- Internal execution services

In future versions, all user-uploaded or AI-generated code must run inside a restricted and disposable execution environment.

User code must never run directly through an unrestricted host command such as:

```python
subprocess.run(user_code)
```

Docker improves isolation, but Docker alone does not guarantee complete security. Future execution must also include resource restrictions, timeouts, limited permissions, and network controls.

---

## 10. Future Docker Execution Flow

Docker execution is not part of Version 0.1.

When added, the flow should be:

```text
Code submitted
      |
      v
Backend creates temporary workspace
      |
      v
Code and generated tests are written to workspace
      |
      v
Restricted Docker container starts
      |
      v
Tests run with limits
      |
      v
Output is collected
      |
      v
Container and temporary files are removed
```

Execution should include:

- Maximum execution time
- Memory limit
- CPU limit
- Process limit
- Read-only files where possible
- Disabled or restricted networking
- Non-root container user
- Automatic cleanup

---

## 11. Version-Based Architecture Evolution

### Version 0.1

```text
Frontend
   |
   v
FastAPI
   |
   v
Placeholder response
```

Features:

- Code input
- POST request
- Input validation
- Placeholder result
- Result display

---

### Version 0.2

```text
Frontend
   |
   v
FastAPI
   |
   v
LLM Provider
```

Features:

- Prompt creation
- Real test generation
- LLM response parsing
- Error handling

---

### Version 0.3

```text
Frontend
   |
   v
FastAPI
   |
   +----> LLM Provider
   |
   v
Docker Test Runner
```

Features:

- Execute generated tests
- Capture output
- Detect pass, failure, timeout, or crash
- Return structured results

---

### Version 0.4

```text
GitHub Repository
       |
       v
Repository Import
       |
       v
File Selection
       |
       v
Test Generation
```

Features:

- Clone repositories
- Inspect project structure
- Select supported files
- Generate tests for repository code

---

### Later Versions

```text
Frontend
   |
   v
FastAPI API Layer
   |
   v
Verification Workflow
   |
   +--> Repository Analysis
   +--> Test Generation
   +--> Test Execution
   +--> Failure Analysis
   +--> Patch Generation
   +--> Verification Report
```

Agent frameworks, queues, Redis, databases, and separate services should only be introduced when the simple architecture can no longer support the required workload.

---

## 12. Architectural Principles

### Keep the architecture simple

Do not introduce infrastructure for hypothetical future problems.

### Separate responsibilities

The frontend handles presentation.

The backend handles application logic.

The execution environment handles untrusted code.

### Depend on interfaces

Application logic should not be tightly coupled to one LLM provider, testing framework, or execution engine.

### Prefer replaceable components

For example, the backend should eventually use an interface such as:

```python
class LLMProvider:
    def generate_tests(self, code: str) -> str:
        ...
```

This allows the provider to be replaced without rewriting the complete application.

### Make failure explicit

Every operation should return a clear result such as:

- Success
- Validation error
- Generation error
- Compilation error
- Test failure
- Timeout
- Execution error

### Never trust generated output

LLM-generated tests and patches must be treated as untrusted input.

They must be validated and executed in isolation.

---

## 13. What Verix Is Not Using Yet

Do not add the following during Version 0.1:

- PostgreSQL
- MongoDB
- Redis
- Celery
- RabbitMQ
- Kafka
- LangGraph
- Tree-sitter
- Kubernetes
- Authentication
- Microservices
- Vector databases
- Background workers
- GitHub integration

These may be introduced later only when required by a specific feature.

---

## 14. Decision Log

Important architectural decisions should be recorded here.

### Decision 001: Separate frontend and backend

**Choice:** Use Next.js for the frontend and FastAPI for the backend.

**Reason:**

- The user interface benefits from React and Next.js.
- Python has a strong testing and AI ecosystem.
- Future Docker and test-runner logic belongs on the server.
- API keys and execution controls must not be exposed to the browser.

---

### Decision 002: Use one repository

**Choice:** Keep the frontend and backend in one Git repository.

**Reason:**

- Easier development
- Easier version coordination
- One issue tracker
- One project history
- Appropriate for the current project size

---

### Decision 003: Start without a database

**Choice:** Do not use a database in Version 0.1.

**Reason:**

The first version only receives code and returns generated tests. No information needs to persist between requests.

---

### Decision 004: Start without microservices

**Choice:** Use one FastAPI backend.

**Reason:**

Microservices would introduce unnecessary deployment, communication, debugging, and monitoring complexity.

---

## 15. Current Architecture Summary

```text
verix/
├── frontend/       Next.js user interface
├── backend/        FastAPI application logic
├── PROJECT.md      Product scope and roadmap
├── ARCHITECTURE.md Technical structure and decisions
├── TODO.md         Current development tasks
└── README.md       Setup and usage instructions
```

Current request flow:

```text
User
  |
  v
Next.js form
  |
  v
POST /generate
  |
  v
FastAPI request validation
  |
  v
Placeholder test response
  |
  v
Result displayed to user
```

This architecture should remain simple until the current version is complete and a real limitation requires it to evolve.