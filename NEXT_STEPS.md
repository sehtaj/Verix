# Verix: Product Handoff and Next Plan

## Active goal: recruiter-ready Python release

**Status:** In progress on `feature/frontend`. This section is the durable
progress ledger for the active goal. Historical statements elsewhere in this
document describe previously reviewed behavior; they are not fresh evidence
that the recruiter-ready acceptance criteria are complete.

The release is complete only when every item below has current evidence:

- [x] Reproducible Python examples have documented expected behavior, known
  defects, and immutable revisions.
- [x] Every generated-test report identifies its expected-behavior sources and
  separates explicit evidence from AI assumptions.
- [ ] Generated tests cover meaningful normal, boundary, invalid-input, and
  error-handling behavior using black-box and gray-box reasoning.
- [x] Existing-suite branch coverage and incremental generated-test branch
  coverage are measured and reported separately.
- [x] The product summarizes what passed, failed, was assumed, and remains
  untested without claiming that code is error-free.
- [x] Failure investigation is grounded in bounded execution evidence.
- [x] Patch verification requires explicit approval and runs the exact reviewed
  patch against both the generated test that exposed the defect and the
  existing suite in a disposable isolated workspace.
- [x] A public demo has bounded request size, execution concurrency, request
  rate, LLM spending, resource use, and cleanup.
- [ ] The current LLM is benchmarked on the reproducible examples; any model or
  OpenRouter change is evidence-driven and separately approved for cost and
  data sharing.
- [ ] The frontend and backend are deployed only after hosting, budget,
  credential, and publishing approval.
- [ ] The deployed journey is verified and the README, architecture
  explanation, screenshots, and short demo walkthrough match the real system.

### Implemented before this goal

- The responsive Next.js verification workspace and its complete five-stage
  repository flow have been implemented and locally reviewed.
- Public GitHub repository targeting is bounded and pinned to an immutable
  commit SHA.
- Existing and generated tests run separately in disposable Docker workspaces
  with resource limits, offline test execution, bounded output, and cleanup.
- Investigation uses a deterministic backend outcome and bounded execution
  evidence before Gemini explains it.
- A one-file source patch is validated, displayed for review, and requires an
  explicit approval action before temporary application.
- Local review evidence previously recorded 155 backend tests, 13 frontend
  tests, a production frontend build, and desktop/tablet/mobile browser checks.
  These historical results will be rerun where relevant before release.

### Implemented during this goal

- Approval now carries the exact generated pytest module displayed beside the
  reviewed patch. The backend validates it before repository preparation.
- The patched disposable workspace runs the existing suite first and the
  generated exposing test second, returning independent results for both.
- Nested-project target paths are translated to the selected project workspace
  before the generated test is written, while the public contract retains the
  repository-relative target.
- The verification screen shows existing-suite and exposing-test evidence
  separately. A successful verification requires the exposing test to pass and
  permits the existing side only to pass or honestly report no collected tests.
- Three deterministic Python fixtures and a machine-readable integrity catalog
  now define explicit contracts, known defects, expected outcomes, test-design
  categories, assumptions, and immutable local revisions.
- Project-root README behavior documentation is now selected deterministically,
  fetched under the existing per-file and total-context limits, included in the
  untrusted Gemini context, and shown distinctly in the context preview.
- Generated-test responses now carry exact bounded source excerpts and an
  explicit assumptions list. The backend rejects citations that do not match
  the selected source, documentation, existing tests, or configuration.
- Every generated pytest function now has one validated normal, boundary,
  invalid-input, or error-handling classification and one black-box or
  gray-box strategy label. Missing, duplicate, extra, or invalid case records
  are rejected before repository preparation.
- Pytest repository runs now collect selected-source branch evidence inside the
  existing hardened Docker boundary. Existing coverage, combined coverage,
  branches reached only by generated tests, and still-untested branches remain
  separate. Coverage is explicitly unavailable for tox rather than estimated.
- Generation, investigation, and fix review now share one deterministic
  evidence summary. It separates passing and failing execution, explicit AI
  assumptions, behavior-source paths, missing test categories and strategies,
  and remaining branch gaps, with a permanent non-certainty disclaimer.

### Proposed work for this goal

- Add a repeatable LLM evaluation harness instead of relying on changing
  third-party repositories.
- Add small, cohesive public-demo controls without introducing authentication,
  a database, Redis, a queue, or an autonomous repair loop.
- Review and deploy the verified system after the user approves external
  hosting, costs, credentials, and publication.

### Approved hosted execution direction

- Local development keeps the existing Docker runner.
- The hosted backend uses E2B rather than executing public repositories inside
  Render's FastAPI process.
- Render hosts one free FastAPI worker; Vercel hosts the Next.js frontend.
- E2B dependency installation may use network access, but test commands run
  only after outbound IPv4 and IPv6 access is denied.
- The E2B Hobby allowance is finite and no-card, so provider exhaustion must
  fail closed rather than fall back to unsafe host execution.
- 2026-09-21: Implemented the provider-neutral runner contract and hosted E2B
  adapter. E2B workspaces are uploaded to short-lived sandboxes, dependency
  installation retains temporary network access, outbound IPv4 and IPv6 are
  denied before tests, the repository becomes read-only before execution, and
  the sandbox is killed on every context exit. Local development still selects
  Docker by default. Render and Vercel configuration is prepared without a
  database, queue, or unsafe subprocess fallback.
- 2026-09-21 verification evidence: 208 backend tests and 150 subtests passed;
  backend compilation, Render YAML validation, `git diff --check`, 19 frontend
  tests, and the Next.js production build passed. The E2B adapter tests use a
  deterministic fake SDK and consume no provider credit. The live E2B template
  and hosted deterministic journey remain unverified until the user creates an
  E2B account and API key. The local Docker journey could not run because
  Docker Desktop was stopped; the Docker CLI reported its missing daemon
  socket before any fixture test executed.

### Progress ledger

- 2026-09-15: Re-read the repository instructions, product, architecture,
  setup, frontend flows, frontend plan, active TODO, Git history, and working
  tree. Confirmed branch `feature/frontend` at `dd481cf`; preserved unrelated
  `.DS_Store` and generated `frontend/next-env.d.ts` changes.
- 2026-09-15: Audited the approval workflow. Confirmed that the approved patch
  is revalidated and applied only in a disposable copy, but the verification
  currently runs only the repository suite. The generated test that exposed a
  defect is not included in the approval request or post-patch run.
- 2026-09-15: Added the recruiter-ready milestone to `TODO.md` and selected the
  exposing-test verification gap as the Current Task.
- 2026-09-15: Completed the exposing-test verification slice. Verification
  now validates and carries the displayed generated test, applies the reviewed
  patch in a disposable copy, and returns separate existing-suite and
  exposing-test results. The frontend review and result screens display that
  distinction and do not call the patch verified when the exposing test fails.
- 2026-09-15 verification evidence: 156 backend unit tests passed; 15 frontend
  tests passed; the Next.js production build and TypeScript validation passed;
  `python3 -m compileall backend` and `git diff --check` passed. No live Docker,
  GitHub, Gemini, or browser journey was claimed for this slice.
- 2026-09-16: Created three dependency-free controlled Python project fixtures:
  a passing existing suite that misses a refund boundary defect, an existing
  shipping suite with one deterministic threshold failure, and an inventory
  project with no tests whose documented exact-stock boundary is defective.
  Each project records its explicit behavior contract, known bug, expected
  evidence, useful black-box/gray-box cases, assumptions, and exclusions.
- 2026-09-16 fixture observation: local pytest produced the documented exit
  codes `0`, `1`, and `5` respectively, with the shipping failure reporting
  `499 != 0` at the exact threshold. This is not accepted as isolated release
  evidence because Docker Desktop was not running; the Docker API socket was
  absent. The fixtures still require a runner-image execution check.
- 2026-09-16: Added a machine-readable example catalog pinned to clean local
  commit `20419fc368506f086eb6a973dfa43a1e5f67af7c`. It records safe project and
  target paths, explicit specification sources, expected outcomes, required
  normal/boundary/invalid/error cases, black-box/gray-box strategies,
  assumptions, untested areas, and per-file SHA-256 integrity hashes. Four
  deterministic tests validate that data without executing fixture code.
- 2026-09-16 publication check: `https://github.com/sehtaj/Verix` returned HTTP
  200 without authentication, confirming the repository is public. The pinned
  fixture commit has not been pushed, so the catalog honestly reports
  `pending_approved_push`; the examples are not yet publicly runnable.
- 2026-09-16: Added bounded behavior-documentation context. A selected
  project-root README now flows through deterministic path selection, size-
  limited GitHub fetching, prompt construction, API presentation and runtime
  validation, and the frontend preview. Repository text remains untrusted data.
- 2026-09-16 verification evidence: 161 backend unit tests passed; 15 frontend
  tests passed; backend compilation and the Next.js production build with
  TypeScript validation passed.
- 2026-09-16: Completed generated-test provenance in commit `1805a38`. Gemini
  must return generated code, bounded source citations, explicit assumptions,
  and its model identifier. Exact citation excerpts are checked against the
  bounded context and displayed beside generation and investigation evidence.
- 2026-09-16 provenance verification evidence: 164 backend tests passed; 16
  frontend tests passed; backend compilation, `git diff --check`, and the
  Next.js production build with TypeScript validation passed. No live Gemini,
  Docker, or browser run was claimed.
- 2026-09-16: Added one-to-one test-intent classification for every generated
  pytest function. The report records category, strategy, and expected
  behavior, while the prompt avoids inventing tests solely to fill labels.
- 2026-09-16 classification verification evidence: 165 backend tests passed;
  17 frontend tests passed; backend compilation and the Next.js production
  build with TypeScript validation passed. Semantic quality across all four
  categories and both strategies remains unproven until the controlled LLM
  benchmark runs.
- 2026-09-16: Added branch coverage for pytest projects using a pinned
  coverage.py runner copied into the hardened test image. Repository coverage
  configuration is ignored, only the selected source is reported, and raw
  executed branch pairs are validated before existing and generated evidence
  is combined.
- 2026-09-16 branch-coverage verification evidence: 172 backend tests and 18
  frontend tests passed; backend compilation and the Next.js production build
  with TypeScript validation passed. The Docker image built successfully. A
  real isolated `refund_boundary` run produced 3 passing existing tests, one
  failing generated day-30 test, existing coverage of 8/12 branches (66.7%),
  combined coverage of 9/12 (75.0%), a generated delta of one branch, and three
  still-untested branches. Coverage remains explicitly unavailable for tox.
- 2026-09-16: Added a bounded evidence summary derived only from validated
  generated-test metadata and isolated execution facts. Its assessment is
  `observed_failures`, `incomplete`, or `no_observed_failures`; even the last
  state carries an explicit statement that evidence does not prove correctness.
- 2026-09-16 evidence-summary verification: 175 backend tests and 19 frontend
  tests passed; backend compilation, `git diff --check`, and the Next.js
  production build with TypeScript validation passed. No new live Gemini,
  GitHub, Docker, or browser journey was claimed for this deterministic UI/API
  aggregation slice.
- 2026-09-16: Added a repeatable Docker-backed recruiter-journey validator for
  every pinned example. It integrity-checks catalog files, preserves documented
  behavior provenance, covers normal, boundary, invalid-input, and
  error-handling cases with black-box and gray-box design, runs pre-fix evidence,
  classifies the outcome deterministically, validates one review-only patch,
  records explicit approval, and reruns both existing and exposing tests in a
  disposable copy without changing the fixture or GitHub.
- 2026-09-16 controlled journey evidence: `refund-boundary` preserved a passing
  existing suite and a failing generated boundary test; `shipping-threshold`
  preserved an existing-suite failure; `inventory-reservation` preserved the
  no-tests result. All three exposing tests passed after their exact reviewed
  patches, the source fixtures remained unchanged, and branch coverage was
  collected for every pre-fix run. The complete backend suite passed 178 tests;
  backend compilation and `git diff --check` passed. This validation used
  pinned deterministic generation artifacts, not live Gemini output; provider
  quality remains the separate benchmark task and is not being claimed here.
- 2026-09-16: Added public-demo admission and cleanup controls. Request bodies
  are capped at 256 KiB, pasted code at 64 KiB, repository URLs at 2,048
  characters, expensive workflows at two concurrent jobs without an unbounded
  queue, each client at 30 modifying requests per rolling minute, and LLM use
  at 100 conservatively weighted calls per rolling day. Gemini output is capped
  at 4,096 tokens per call. All ceilings are positive-integer environment
  settings so production can lower them without code changes.
- 2026-09-16 cleanup evidence: runtime workspaces now use one private,
  Verix-owned temporary root. Context managers remove normal workspaces and a
  one-hour sweep removes only stale regular directories with recognized Verix
  prefixes. The full three-example Docker journey still passed, its temporary
  root was empty afterward, and Docker reported no remaining Verix containers.
  The complete backend suite passed 188 tests; backend compilation and
  `git diff --check` passed.
- Public-demo limitation: rate and rolling LLM-call counters are intentionally
  in-process to avoid prematurely adding a database, Redis, or a queue. The
  first deployment must therefore use one backend worker and a provider-side
  hard spending/quota cap. Multiple workers would multiply these local limits.
- 2026-09-16: Added a repeatable configured-model benchmark harness. It builds
  the same bounded generation context used by production from each integrity-
  checked fixture, makes at most eight LLM calls, runs generated tests in
  Docker against both the known defect and the catalog correction, compares
  required categories, strategies, documentation grounding, and assumptions,
  checks the evidence-grounded investigation wording, and structurally
  validates review-only proposals without approving or applying them.
- 2026-09-16 benchmark-harness verification: 190 backend tests passed; backend
  compilation and `git diff --check` passed. No live Gemini call was made. The
  attempted run was stopped before transmission because explicit approval is
  still required to send the three controlled example sources, tests, and
  documentation files to Gemini and consume eight configured-provider calls.
- 2026-09-16 dry-run disclosure: the proposed benchmark would send 7,214 bytes
  of controlled fixture context to the configured Google Gemini API using
  `gemini-3.5-flash`: 2,763 bytes for refund, 2,287 bytes for shipping, and
  2,164 bytes for inventory. It would make at most eight calls, include no
  secrets, and neither approve nor apply a generated patch. The manifest is
  reproducible with `python3 backend/scripts/benchmark_configured_llm.py
  --dry-run` and performs no external request.
- 2026-09-16 live baseline benchmark: the user approved one run. Three Gemini
  calls were made—one per example generation stage, below the eight-call cap.
  Refund and shipping returned responses that failed Verix's strict generated-
  report validation; inventory returned an API-generation failure. Therefore
  no generated suite reached Docker, investigation, or proposal evaluation,
  and the configured setup scored 0 of 3 valid generation reports. No patch
  was approved or applied and no automatic retry was performed.
- The baseline failure does not yet justify changing provider: Verix had asked
  for JSON only in prompt prose despite the installed Gemini client supporting
  native JSON Schema. The adapter now supplies explicit JSON response schemas
  for generated-test reports and fix proposals while retaining deterministic
  backend validation. The benchmark also records invalid generation as a model
  miss and can continue selected examples without repeating completed calls.
  This corrective configuration is locally verified by 192 passing backend
  tests, backend compilation, and `git diff --check`, but has not been live-
  retested because the user approved only one benchmark run.
- 2026-09-16 schema-enforced retry: the user approved one retry. Three further
  Gemini calls were made, one per generation stage. Refund returned an API
  generation failure; shipping and inventory again returned reports rejected
  by Verix's evidence validation. The retry therefore also scored 0 of 3, no
  generated test reached Docker, and no investigation or patch was produced.
  Across both approved runs, six calls were made and no patch was approved or
  applied. The configured `gemini-3.5-flash` setup is not acceptable for the
  recruiter-ready release.
- 2026-09-16 model migration: the direct Google adapter now targets stable
  `gemini-3.8-flash`. This preserved the existing provider, API key boundary,
  privacy path, structured-output validation, and benchmark fixtures; no
  OpenRouter or multi-provider abstraction was added.
- 2026-09-16 failure diagnosis: repeated schema-constrained 3.8 Flash requests
  reached Google but returned terminal `503 UNAVAILABLE` high-demand responses
  before generation. A simple 3.8 request succeeded once, so the configured
  key, SDK, and model identifier are valid. Equivalent structured requests to
  3.7 and 3.6 Flash also returned 503, while 2.5 Pro is unavailable to new
  users. These results identify provider capacity, not Verix parsing, as the
  current 3.8 blocker.
- A controlled 2.5 Flash request using the same prompt, schema, and 4,096-token
  cap exposed a separate proven cause of earlier invalid JSON: the response
  ended with `MAX_TOKENS` after 1,305 prompt tokens, 2,463 hidden thinking
  tokens, and 1,619 candidate tokens, leaving a truncated JSON object. The 3.8
  adapter now requests the supported low thinking level and preserves safe
  private diagnostics for API status, finish reason, and report validation.
  This correction is covered by local tests but is not claimed as live-proven
  on 3.8 because every subsequent structured request stopped at Google's 503.
- 2026-09-16 post-diagnosis verification: 196 backend tests plus 138 subtests,
  19 frontend tests, backend compilation, the frontend production build and
  TypeScript validation, and `git diff --check` passed. The configured-model
  dry run still targets 3.8 Flash, includes 7,214 bytes of controlled fixture
  context, makes at most eight calls, contains no secrets, and cannot approve
  or apply a patch.
- 2026-09-16 deterministic Docker review: all three pinned recruiter journeys
  passed against Docker 29.7.2. Refund preserved a passing existing suite and
  a generated boundary failure; shipping preserved an existing-suite failure;
  inventory preserved the no-tests result. Each exact reviewed correction made
  its exposing test pass in a disposable workspace, the original fixtures
  stayed unchanged, and GitHub remained unchanged. This validates Verix's
  deterministic workflow, not the unavailable live model.
- 2026-09-16 local browser review: the initial workspace, inline invalid-URL
  recovery, live public GitHub context, selected target, related-test context,
  and bounded context-preview dialog worked through the real Next.js/FastAPI
  boundary. The Verix repository resolved to one full commit SHA and the
  preview exposed five bounded files totaling 43,805 bytes without contacting
  Gemini or executing repository code. Desktop and 390-by-844 mobile checks
  preserved readable controls, status text, keyboard semantics, and the mobile
  repository drawer. The current CORS allowlist correctly accepted local port
  3000 and rejected port 3001; production therefore still requires an approved
  environment-configured Vercel origin rather than another hard-coded domain.
- Production-readiness audit initially found hard-coded local CORS origins,
  incomplete environment examples, and environment loading that occurred only
  while constructing Gemini after resource settings were read. Environment
  loading is now centralized before CORS, limits, and Gemini initialization;
  exact trusted frontend origins are configurable with `VERIX_CORS_ORIGINS`;
  unsafe wildcard, credential, path, query, fragment, malformed-port, and empty
  values fail closed; localhost defaults remain unchanged. Backend and frontend
  environment examples now document the API URL, CORS origin, and bounded demo
  settings. Host-supplied values retain precedence over local `.env` values.
- 2026-09-16 production-configuration verification: 199 backend tests plus 147
  subtests, 19 frontend tests, the frontend production build and TypeScript
  validation, backend compilation, and `git diff --check` passed. Actual
  production values remain intentionally unset until the user chooses the
  Docker-capable backend host, budget, public API URL, and Vercel origin.
- 2026-09-16 recruiter-release Review Phase: synchronized `PROJECT.md`,
  `ARCHITECTURE.md`, and `README.md` with grounded test provenance, explicit
  assumptions, per-test classifications, pytest branch coverage, evidence
  summaries, exact exposing-test verification, public-demo controls, the 3.8
  model adapter, strict production configuration, and the non-certainty product
  claim. Removed stale statements that Verix proves correctness or has no
  coverage. Final backend evidence after configuration hardening is 199 tests
  plus 150 subtests passed; compilation and `git diff --check` also passed.
- 2026-09-21 bounded provider probe: after five days without retrying, the
  benchmark harness was tightened so `--generation-only` requires exactly one
  selected example, discloses only that payload, and cannot continue into
  Docker execution, investigation, or proposal generation. The disclosed
  `refund-boundary` probe sent 2,763 bytes in one call to configured
  `gemini-3.8-flash`; Google again returned terminal `503 UNAVAILABLE` before
  producing a report. No generated code was executed and no patch was proposed,
  approved, or applied. The full benchmark was correctly not started.
- 2026-09-21 official-model audit: Google's current model documentation lists
  `gemini-3.8-flash` as stable/GA with structured outputs and low, medium, and
  high thinking support, while its pricing page lists free-tier input and
  output tokens. This rules out an obsolete identifier, unsupported response
  schema, unsupported low thinking, or paid-only model access as the cause of
  the probe failure. The terminal 503 remains provider-side availability
  evidence. Sources: `https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash`
  and `https://ai.google.dev/gemini-api/docs/pricing`.
- 2026-09-21 verification after the probe and production-configuration review:
  200 backend tests plus 150 subtests and 19 frontend tests passed. Backend
  compilation, the Next.js production build and TypeScript validation, and
  `git diff --check` also passed.

### Exact next action

Do not repeat the full benchmark or another probe while Google's structured 3.8
endpoint continues returning terminal 503 responses. The five-day follow-up
probe confirmed that provider capacity has not recovered. Resume model
evaluation only after an observable provider-state change or after the user
approves a different model/provider and its cost and data-sharing terms. Keep
the one-call generation probe as the gate before any future full benchmark.

The recruiter-release Review Phase and provider-independent configuration code
are complete. The next external decision is the Docker-capable backend host,
monthly budget, public backend URL/domain plan, and intended Vercel origin.
After those are approved, add only the selected host's minimal deployment
artifacts and configure the documented environment contract. The 3.8 benchmark
still resumes separately with one targeted request only after provider capacity
recovers.

### Decisions that will require the user later

- Backend hosting provider, expected monthly budget, and deployment credentials.
- Permission to publish the deterministic demo repositories and production URLs.
- Any LLM model/provider change that affects cost or repository-data handling.

> Read this document at the start of a new Verix conversation. It records the
> product decisions, current implementation, safety boundaries, and agreed
> direction after V1.0. It is a planning handoff, not an authorization to add
> every future feature at once.

## One-sentence product description

Verix is a Python-first AI software quality engineer for **public GitHub
repositories**: it gathers bounded repository evidence, runs tests in an
isolated environment, generates focused pytest tests, explains evidence-based
outcomes, proposes one reviewable source-only patch, and can verify an
explicitly approved patch in a disposable workspace without changing GitHub.

Its motto is:

> Trust your code before you trust your AI.

## The problem Verix is solving

AI coding tools can write code quickly, but generated code is not automatically
correct. Developers still need to understand the project, think about edge
cases, write and run tests, investigate failures, review a possible fix, and
decide whether that fix deserves trust.

Verix is not meant to be another chat interface that claims a change is right.
Its purpose is to create **evidence** that helps a developer make a better
decision.

The central product claim should be:

> Verix increases confidence by testing and validating code; it does not prove
> that code is perfect.

## What has been completed

All work through V1.0 is complete. The current repository supports the whole
bounded repository-verification flow for public Python projects:

```text
Public GitHub repository
  -> choose revision, optional project folder, and Python source target
  -> inspect a bounded context preview
  -> run existing tests or generate focused pytest tests
  -> preserve separate existing and generated test evidence
  -> investigate one deterministic outcome
  -> review one validated source-only fix proposal
  -> explicitly approve temporary verification
  -> run the reviewed patch in a fresh disposable workspace
  -> show the patched-suite result; GitHub stays unchanged
```

### Product progression

The project deliberately grew in small steps:

1. **Client/server proof** — FastAPI health/generation endpoint and a Next.js
   page proved browser-to-backend communication.
2. **LLM test generation** — Gemini generated pytest code while the API key
   remained on the backend.
3. **Safe execution** — submitted and generated code began running only inside
   bounded Docker containers.
4. **Public GitHub context** — Verix learned to validate public GitHub URLs,
   fetch metadata, inspect a bounded tree, identify Python paths, and infer
   project setup.
5. **Existing repository tests** — it began preparing public Python archives,
   installing dependencies in a disposable environment, and running pytest or
   tox safely.
6. **Repository-aware generated tests** — it selects one target plus small
   related context, asks Gemini for focused tests, validates that generated
   Python, and runs original/generated suites separately.
7. **Evidence-grounded investigation** — deterministic backend logic classifies
   the run before Gemini explains the bounded evidence.
8. **Developer targeting** — users can choose a branch/tag/commit, nested
   project directory, and verified Python target, and preview the exact context
   before generation.
9. **Review-only fix proposal** — Gemini can propose one limited Python diff;
   Verix validates it but does not apply it.
10. **Explicit temporary verification** — a developer can approve the exact
    reviewed diff for application and testing in a temporary copy only.
11. **V1.0 frontend review** — the old prototype UI was replaced by the
    responsive Stitch-derived verification workspace, connected to real API
    data and reviewed for accessibility and responsive behavior.

## What the user can do in the current website

The browser workflow is a five-stage workspace:

```text
Context -> Run Tests -> Investigate -> Review Fix -> Verify
```

The user can:

1. Start a verification with a canonical public GitHub repository URL.
2. Optionally specify a branch, tag, or full commit SHA.
3. Optionally specify a repository-relative Python project directory.
4. Fetch repository metadata, a bounded tree, detected setup, and a test plan.
5. Keep the automatic target or choose another backend-verified Python file.
6. Preview the exact bounded source, related tests, and configuration content
   that could be sent to the LLM.
7. Run the repository's existing suite.
8. Generate focused pytest tests and run both original and generated suites
   separately.
9. Inspect preparation, dependency-installation, runner, output, pass/failure,
   no-tests, timeout, and skipped evidence.
10. Investigate the evidence and receive a bounded explanation.
11. Request a source-only fix proposal when the outcome is eligible.
12. Review the proposal, including its pinned revision and unified diff.
13. Explicitly approve temporary verification of exactly that reviewed patch.
14. Inspect the patched-suite result and the confirmation that GitHub was not
    changed.

The redesigned browser page intentionally focuses on this repository journey.
The older pasted-code endpoint (`POST /generate`) remains available for API
clients but is not rendered as the main browser experience.

## Current architecture

```text
Browser
  -> Next.js / React frontend
  -> typed API client
  -> FastAPI backend
       -> GitHub public API
       -> Gemini API
       -> isolated Docker execution
```

### Frontend responsibilities

The frontend owns rendering and browser-held interface state only.

- `frontend/app/page.tsx` chooses the current screen.
- `frontend/hooks/use-repository-workflow.ts` coordinates browser workflow
  state, actions, stale-request rejection, recovery, and reset confirmation.
- `frontend/lib/api.ts` owns typed backend requests and runtime validation of
  response shapes and pinned targeting facts.
- `frontend/lib/repository-results.ts` contains deterministic display-only
  mappings for results and workflow status.
- `frontend/components/verix/` contains typed presentational screens.

The frontend must not duplicate backend business logic, execute repository
code, contain API keys, or decide whether a test outcome is factual.

### Backend responsibilities

The backend owns all business logic and external coordination.

- FastAPI routes validate requests and translate expected errors.
- GitHub services retrieve bounded public repository evidence.
- Repository services select safe context, plans, targets, dependency commands,
  and test commands.
- Workflow modules coordinate execution, investigation, fix proposal, and fix
  verification.
- Gemini generates tests, explanations, and review-only patch proposals.
- Docker executes repository dependency setup and tests.

The backend, not the model, determines factual outcomes such as setup failure,
no tests, test failure, timeout, or pass.

## The current "agent" model

Verix does not yet have an unrestricted autonomous coding loop. That is
intentional.

It currently has three bounded AI actions:

1. **Test-generation action** — Gemini receives focused selected context and
   produces one pytest module.
2. **Investigation action** — Gemini receives a deterministic outcome plus
   bounded command evidence and explains it.
3. **Fix-proposal action** — Gemini receives a pinned failure context and
   proposes one minimal source-only unified diff.

The model cannot browse arbitrary content, run arbitrary commands, change
GitHub, retry forever, decide the factual test result, or apply a patch without
the developer's explicit approval.

This is best described as an **AI-assisted, safety-bounded software quality
engineer**, not a fully autonomous software engineer.

## Safety model that must not be weakened

Repository code, generated tests, dependency build scripts, and submitted code
are untrusted. They must never execute directly in the FastAPI host process.

Important existing protections include:

- Public canonical `github.com/owner/repository` URLs only.
- Validation of branch/tag/commit, subdirectory, and selected Python target.
- One immutable commit SHA preserved through context, generation, archive
  retrieval, execution, investigation, proposal, and verification.
- Bounded repository tree and bounded LLM context.
- Archive limits, safe extraction, and rejection of links/path traversal.
- Fixed backend-selected dependency and test commands; never run repository
  supplied shell commands.
- Disposable workspaces with cleanup.
- Docker resource limits, timeouts, non-root execution, capability reduction,
  no network for test runs, and read-only repository mounts for tests.
- Separate evidence for existing and generated suites.
- Generated Python validation before it enters the disposable workspace.
- Source-only patch validation before temporary patch application.
- Explicit developer approval before verification.
- No GitHub writes, commits, pull requests, or local-checkout modification.

Docker isolation reduces risk but the current local-Docker design is **not** a
complete production-grade multi-tenant sandbox. Do not claim otherwise.

## What a good Verix result should say

Verix should never say:

> "This code has no errors."

No test system can prove that for arbitrary software. Instead, Verix should
report an evidence-bound confidence statement, for example:

```text
Verification confidence: medium

✓ Existing suite passed
✓ Generated edge-case tests passed
✓ Important branches were exercised
✓ Invalid-input behavior was checked
⚠ Expected behavior was inferred from code, not a written specification
⚠ Large-input performance was not evaluated
⚠ Concurrent behavior was not evaluated
```

The statement must identify the scope of what was tested and what remains
unknown.

## Testing concepts that guide the product

### Test level versus test design

These are separate dimensions:

```text
Unit / integration / contract / end-to-end = how much of the system is tested
Black-box / white-box / gray-box           = how the test is designed
```

- **Black-box tests** validate observable inputs, outputs, and errors against a
  public contract. They should be the default for public functions and APIs.
- **White-box tests** deliberately exercise branches, exception handlers,
  loops, and rare implementation paths. Use them to close meaningful coverage
  gaps, but avoid coupling tests tightly to private implementation details.
- **Gray-box tests** use implementation knowledge to find a risk, but assert
  behavior through the public interface. This is often the best general
  strategy for Verix.

### Test types Verix should eventually understand

| Type | Purpose |
| --- | --- |
| Unit | One function/class in isolation |
| Integration | Components and real boundaries working together |
| Contract | API/schema agreement between systems |
| End-to-end | A complete user workflow |
| Regression | A discovered bug stays fixed |
| Property-based | General rules across generated inputs |
| Fuzz | Malformed, unusual, random, or adversarial input |
| Mutation | Whether tests catch small intentional code changes |
| Performance | Time/memory behavior under larger workloads |
| Security | Dangerous patterns and unsafe input behavior |

### The test-oracle problem

Generating inputs is not enough. A test must know the expected result.
Without a clear specification, the LLM may only infer what behavior should be
from code, naming, existing tests, or documentation.

Future Verix reports should distinguish:

```text
Expected behavior source:
  - explicit specification
  - documentation
  - existing test contract
  - inferred from code
  - unknown assumption
```

The confidence of a generated test should be lower when its expected behavior
is only inferred.

### Test quality matters more than test count

Generated tests should be judged for whether they:

- Fail for a real defect and pass for correct behavior.
- Test one meaningful behavior.
- Are deterministic and independent of test order.
- Avoid current time, network, randomness, and shared state unless controlled.
- Assert public behavior rather than brittle implementation details where
  possible.
- Avoid tautologies, duplicate assertions, over-mocking, and reimplementing
  the same possibly-wrong production logic in the test.

### High-value future quality signals

After deployment, prioritize these in order:

1. Generated-test quality analysis and duplicate/brittle-test detection.
2. Meaningful branch/condition coverage gaps.
3. Property-based testing with Python tools such as Hypothesis.
4. Mutation testing to measure whether tests catch realistic mistakes.
5. Flaky-test detection through repeat runs.
6. Static/type/security analysis.
7. Integration/contract testing.
8. Performance and concurrency testing.

Coverage alone must never be presented as proof of quality. A test suite can
have high line coverage while asserting very little useful behavior.

## LLM decision

### Current state

The current backend calls Gemini directly in `backend/services/llm_service.py`
and currently targets stable `gemini-3.8-flash`. The previous configured
`gemini-3.5-flash` baseline failed both controlled benchmark attempts and is no
longer the production model identifier.

### Recommended near-term move

Do not introduce a multi-provider architecture before the Python MVP is
deployed. The direct adapter has already been upgraded to `gemini-3.8-flash`.
Its deterministic local integration is verified, but a valid live structured
response and full benchmark remain blocked by repeated provider-side 503
capacity responses. Resume with one targeted request after capacity recovers;
do not treat repeated retries as evaluation evidence.

The evaluation should measure:

- Valid pytest generation rate
- Correct imports and use of the selected project target
- Useful edge-case coverage
- Test-suite pass/failure behavior
- Investigation grounding in actual evidence
- Patch validity and minimality
- Latency and API cost

### OpenRouter decision

OpenRouter is a multi-model gateway, not inherently a better model. It can be
useful later for controlled model comparisons, selected fallbacks, and provider
experimentation.

Do **not** use uncontrolled cheapest-model or automatic model routing for patch
generation. Repository code, test contents, logs, and patches can be sent to
providers, so privacy, retention, provider choice, and reproducibility matter.

If OpenRouter is added later:

- Add one provider interface in the backend; do not spread provider checks
  across workflows.
- Select explicit models for each action.
- Record the actual model/provider used with the generated evidence.
- Prefer no-data-collection choices where appropriate.
- Keep model fallbacks controlled, especially for fix proposals.
- Preserve all existing validation, sandboxing, and explicit approval rules.

## Deployment reality

### What Vercel can host

Vercel is an excellent home for the Next.js frontend.

If only the frontend is deployed, a recruiter can view the interface, but real
workflow actions will fail because the default API URL is
`http://localhost:8000`. In a visitor's browser, `localhost` means the
visitor's own computer, not the Verix backend.

### What the full deployed product needs

```text
Recruiter browser
  -> Vercel-hosted Next.js frontend
  -> public FastAPI backend URL
  -> temporary isolated Docker/container execution
  -> GitHub public API + Gemini API
```

The frontend environment must point at the hosted backend:

```text
NEXT_PUBLIC_API_URL=https://api.example.com
```

The backend must allow only the actual frontend origin through CORS, keep the
LLM key private, and have a Docker-capable execution environment.

### Why a server or sandbox is still required

Serverless hosting does not eliminate the need to isolate untrusted code.
Repository code, generated tests, and dependency installation can consume CPU,
memory, disk, processes, or network access, and cannot be reliably classified
as safe before execution.

The production shape can be serverless from the user's perspective, but code
still needs a temporary container or microVM under the hood.

For the current architecture, the simplest deployment is:

```text
Vercel: frontend
One Docker-capable Linux VPS: FastAPI + controlled Docker runner
```

AWS is optional. A small Docker-capable Linux VPS from any reputable provider
can run the backend. Do not move to complicated Kubernetes, queues, databases,
or cloud-specific infrastructure for the first demo.

### Cost expectations

A frontend-only Vercel preview can be free or nearly free at small personal
usage. A fully working demo has possible costs from backend compute, Docker
test runs, AI tokens, and optionally a domain.

For a small recruiter demo, costs can remain low with strict limits. A public,
unlimited code-execution and LLM service should not be assumed to remain free.

## Python-only MVP finish plan

The immediate goal is not more functionality. It is a deployable,
recruiter-ready public Python MVP.

### Scope to keep

- Public GitHub Python repositories only.
- pytest and tox support.
- Selected revision, project folder, and Python target.
- Existing test runs, generated tests, investigation, proposal, and temporary
  verification.
- Explicit user approval before any patch is tested.

### Scope to postpone

- Additional languages.
- Private repositories, GitHub Apps, and pull requests.
- User accounts, authentication, teams, databases, queues, or saved history.
- Reports/analytics implementation.
- CI integration.
- Autonomous retry loops or automatic real-world code changes.
- Broad OpenRouter/multi-provider support.

### Work sequence

#### 1. Decide the deployment target

Choose one small Docker-capable Linux server provider. The decision should be
made before production implementation because the backend's execution model
depends on it.

Target outcome:

```text
One server can run FastAPI and create bounded temporary Docker containers.
```

#### 2. Add production-demo guardrails

Before public sharing, add the smallest necessary protections:

- Low global concurrency for expensive test runs.
- Per-IP request limits suitable for a single-process demo backend.
- Existing strict archive/output/time/resource limits preserved.
- Explicit request-size limits where missing.
- Clear error messages that do not expose secrets or internal paths.
- Spending alerts and hard limits for the LLM account.

Do not add a database or Redis just for the first demo unless a real limitation
requires it.

#### 3. Upgrade and benchmark the LLM

Use a small, fixed Python evaluation set before changing the production model:

- A repository with passing tests.
- A repository with a known existing-test failure.
- A repository with no tests.
- A nested Python project folder.
- A small target with meaningful edge cases.
- A known fix-proposal/temporary-verification case.

Record success rate, import correctness, test quality, patch validity, latency,
and cost. Upgrade the direct Gemini model first. Only evaluate OpenRouter if a
benchmark shows a meaningful need.

#### 4. Deploy the backend

Deploy FastAPI and the runner image to the selected server.

Required production configuration:

- Private `LLM_API_KEY` on the server only.
- HTTPS endpoint, for example `https://api.example.com`.
- Firewall allowing only required traffic.
- CORS allowlist for the Vercel frontend domain.
- Docker image built and available to the backend.
- Logs and a basic way to restart the service.
- No secrets in Git or browser environment variables.

#### 5. Deploy the frontend

Deploy `frontend/` to Vercel and set:

```text
NEXT_PUBLIC_API_URL=https://api.example.com
```

Verify that no deployment falls back to `localhost:8000`.

#### 6. Run live end-to-end verification

Use small curated public Python repositories to check the real deployed system:

- Repository context and context preview.
- Existing suite passes.
- Existing suite fails.
- No tests found.
- Dependency/setup failure.
- Generated-test evidence is separate.
- Investigation is grounded in the actual result.
- Proposal is review-only.
- Explicit temporary patch verification produces a separate result.

For a reliable portfolio demo, create a small public demonstration Python
repository with a known bug and deterministic test evidence. Do not depend only
on unrelated public repositories that might change unexpectedly.

#### 7. Prepare the recruiter experience

Create or update:

- A concise README opening section.
- A diagram of the browser -> backend -> Docker architecture.
- Screenshots for pass, failure, investigation, proposal, and verification.
- A short demo video, ideally around 90 seconds.
- A clear limitations/safety section.
- A stable live URL.

The recruiter should understand the problem, flow, safety boundaries, and
technical choices in under two minutes.

## Definition of done for the deployable Python MVP

Call this milestone finished only when all of the following are true:

- The frontend is hosted publicly.
- The backend is hosted publicly on a Docker-capable environment.
- The frontend calls the deployed backend rather than localhost.
- CORS, secrets, HTTPS, execution limits, and basic public-demo limits are
  configured.
- The full workflow works on the deployed system for controlled public Python
  repositories.
- No GitHub repository is changed by Verix.
- The README and demo material accurately describe the product and limitations.
- The user can monitor or cap LLM and compute spending.

## Current repository state and Git notes

At the last frontend review, the working branch was `feature/frontend`. The
three review commits created locally were:

- `adecbd5` — `fix(frontend): harden verification workflow states`
- `2eccdee` — `fix(frontend): complete accessible responsive verification UI`
- `dd481cf` — `docs(frontend): synchronize reviewed workspace documentation`

Local commits are now authorized without per-commit approval. They should be
inspected and pushed only with explicit user approval. Do not commit `.env`
files, API keys, dependency directories, temporary workspaces, build output,
or unrelated `.DS_Store` changes.

## How a new Codex chat should begin

Paste something like this into a new chat:

```text
Read AGENTS.md, PROJECT.md, ARCHITECTURE.md, README.md, TODO.md, and
NEXT_STEPS.md completely. We are finishing the deployable Python-only Verix
MVP. Do not add future features such as private repositories, extra languages,
authentication, databases, CI integration, or autonomous patching. Preserve
the Docker safety boundary. First inspect the branch and working tree, then
propose the smallest next task from NEXT_STEPS.md. You may create small,
verified local commits without asking. Do not push or make an external
deployment without asking me first.
```

## Important principles to preserve

1. The developer stays in control of any real code change.
2. LLM output is evidence to validate, not a source of truth.
3. Deterministic backend facts decide test outcomes.
4. Existing and generated evidence remain separate.
5. Focused bounded context is safer and more useful than sending an entire
   repository to an LLM.
6. Security boundaries must not be weakened to make a demo easier.
7. A passing test suite is useful evidence, not proof of perfect correctness.
8. Finish the Python workflow and deploy it before expanding the product.
