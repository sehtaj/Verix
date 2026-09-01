# Verix Frontend Plan

## Goal

Replace the current single-column prototype with the Stitch-designed Verix verification workspace while preserving the current backend behavior and safety boundaries. The result should feel like one coherent developer tool, not a set of generated mockups.

Work is organized by implementation slices without release labels, and the repository root `TODO.md` remains unchanged.

## Sources of truth

Use these sources in this order when implementing:

1. Current backend request/response contracts and their tests.
2. `frontend/FLOWS.md` for user behavior and state transitions.
3. The four Stitch HTML exports for layout, measurements, hierarchy, and component styling.
4. The matching Stitch PNGs for visual comparison.
5. Stitch `terminal_command_center/DESIGN.md` for tokens and design language.

The HTML exports are visual reference code, not production code. Do not copy their Tailwind CDN, remote image, Material Symbols setup, or embedded instructions into the app.

### Stitch screen mapping

| Stitch folder | Product screen |
| --- | --- |
| `verix_ready_to_generate_tests_master_shell` | New Verification |
| `verix_ready_to_verify_master_shell` | Ready to Verify |
| `verix_ready_to_generate_tests_classic_shell` | Ready to Generate Tests |
| `verix_master_detail_module_detail_layout` | Test Run Found a Failure |

### Corrections to make during implementation

- New Verification starts with no repository, no file tree, and Context active.
- Ready to Verify includes the detected `tests/test_refunds.py` path and must not say that no test files exist.
- Ready to Generate Tests uses `No Existing Tests Found`, without the decorative `STATUS: READY` line.
- Rename `Advanced Options` to `Advanced Test Options`, but do not make it interactive until the backend supports real options.
- Improve low-contrast secondary text while retaining the dark terminal aesthetic.
- Use actual repository and API values instead of hard-coded `acme/payments`, paths, counts, commit hashes, or test results.

## Scope

### Included

- The full-width application shell from Stitch.
- Header, repository context sidebar, and five-step progress bar.
- New Verification form.
- Repository context loading, target selection, and exact-context preview.
- Ready-to-run and no-existing-tests branches.
- Existing-test execution and failure evidence.
- Focused test generation with existing/generated results kept separate.
- Investigation, fix review, explicit approval, and disposable verification states.
- Honest loading, empty, skipped, timeout, error, pass, and failure states.
- Responsive behavior and keyboard/accessibility support.

### Deferred

- Real Explorer, Reports, Settings, notification, and profile features.
- Saved verification history or resumable URLs.
- Authentication or private repositories.
- Backend API changes and new test-generation options.
- Marketing pages.
- Pasted-code generation inside this redesigned workspace.

The deferred header items remain visually present because that layout was chosen, but they must not navigate to fake screens. Until implemented, they should be non-interactive or explicitly unavailable and excluded from the keyboard tab order.

## Design system

### Core tokens

Define semantic CSS variables once in `app/globals.css` and map Tailwind/shadcn to them.

| Role | Value | Use |
| --- | --- | --- |
| Background | `#131313` | App canvas |
| Lowest surface | `#0e0e0e` | Code/log wells and deepest panels |
| Low surface | `#1c1b1b` | Sidebar and cards |
| Surface | `#201f1f` | Raised content panels |
| High surface | `#2a2a2a` | Selected rows and header bars |
| Foreground | `#e5e2e1` | Primary text |
| Muted foreground | `#ddc1ae` | Secondary text, adjusted when necessary for contrast |
| Primary | `#ffb77f` | Buttons, active labels, focus |
| Strong amber | `#ff8a00` | High-attention active state only |
| Outline | `#a58c7b` | Strong borders |
| Subtle outline | `#564334` | Grid and panel dividers |
| Success | `#a8c79c` | Passing/completed states |
| Error | `#ffb4ab` | Failure/error states |

Use the four-pixel spacing grid from the handoff. Keep corners square, avoid shadows, and create depth through surface color and one-pixel borders. Scanline texture should be subtle, non-animated, and absent behind dense code when it hurts readability.

### Typography

- Space Mono: branding, headings, labels, controls, status, and code-like metadata.
- Courier Prime: body copy and explanatory text.
- Preserve a readable fallback monospace stack.
- Self-host through the Next.js font system so production does not depend on the Stitch Google Fonts link at runtime.
- Use tabular numerals for counts, durations, revisions, and line numbers.

### Semantic status language

- Amber: action, current stage, selection, or warning.
- Green: completed or passed.
- Red: failed, invalid, or destructive.
- Neutral: unavailable or upcoming.

Status text and icons are mandatory; color alone is insufficient.

## Application structure

Keep one Next.js workspace route for now. The visible “screens” are states of one active verification, because the backend has no saved verification ID or persistence layer.

```text
frontend/
├── app/
│   ├── globals.css
│   ├── layout.tsx
│   └── page.tsx
├── components/
│   ├── ui/                         # shadcn primitives, restyled to Verix tokens
│   └── verix/
│       ├── app-header.tsx
│       ├── app-shell.tsx
│       ├── workflow-stepper.tsx
│       ├── repository-sidebar.tsx
│       ├── new-verification-form.tsx
│       ├── target-context-panel.tsx
│       ├── context-preview-dialog.tsx
│       ├── execution-actions.tsx
│       ├── execution-summary.tsx
│       ├── execution-logs.tsx
│       ├── generated-tests-panel.tsx
│       ├── investigation-panel.tsx
│       ├── fix-review-panel.tsx
│       └── verification-result-panel.tsx
├── hooks/
│   └── use-repository-workflow.ts
├── lib/
│   ├── api.ts
│   ├── repository-results.ts
│   └── utils.ts
└── types/
    ├── api.ts
    └── workflow.ts
```

This is a target structure, not a requirement to create every file immediately. Extract a component only when it owns a distinct visual or state responsibility. Do not add a state-management library; the workflow is local to one page and the existing hook is an appropriate boundary.

Keep the architecture highly cohesive and loosely coupled: API transport stays in `lib/api.ts`, workflow coordination stays in the repository hook, deterministic display classification stays in pure helpers, and components receive typed data and callbacks instead of importing workflow or transport internals.

## State architecture

### API data

Keep the existing typed response models and expand them only when a current screen needs a precise view type. API field names should remain faithful to the backend at the network boundary.

### UI state

Add a small discriminated workflow state instead of inferring the entire screen from many nullable result objects. Suggested screen values:

```text
new_verification
loading_context
ready_existing_tests
ready_generate_tests
running_existing_tests
showing_test_result
generating_tests
showing_generation_result
investigating
showing_investigation
proposing_fix
reviewing_fix
verifying_fix
showing_verification_result
```

Keep returned API data separately from the screen name. A screen transition must not rewrite backend evidence.

### Result helpers

Place deterministic display helpers in `lib/repository-results.ts`, including:

- installation state: passed, failed, timed out, skipped;
- execution state: passed, failed, timed out, skipped, or no tests collected;
- screen branch from the context test-path count;
- progress-step status from the workflow screen;
- human-readable outcome labels.

These helpers are frontend presentation logic only. They must not replace the backend investigation outcome.

## API integration map

| User action | Endpoint | Required UI result |
| --- | --- | --- |
| Fetch Repository | `POST /repository/context` | Pinned revision, tree, setup, test plan, default target |
| Change Target | `POST /repository/context` | Backend-verified target and refreshed selection |
| Preview Context | `POST /repository/context/preview` | Exact bounded source/test/config content |
| Run Existing Tests | `POST /repository/test-run` | Preparation, setup, runner, existing execution |
| Generate Focused Tests | `POST /repository/generate` | Generated code and separate existing/generated execution |
| Investigate | `POST /repository/investigate` | Fixed outcome, explanation, code, and separate evidence |
| Propose Source Fix | `POST /repository/fix-proposal` | Pinned, validated, unapplied one-file diff |
| Approve and Verify | `POST /repository/fix-verify` | Patched-suite evidence and explicit GitHub-unchanged facts |

Improve `lib/api.ts` during implementation so it safely handles non-JSON responses and preserves backend `detail` messages. Do not send optional fields as empty strings.

## Component behavior

### App header

- Match the Stitch height, borders, typography, spacing, and repository chip.
- Verix and New Verification are real controls.
- Verifications identifies the current product area.
- Preserve Explorer, Reports, Settings, notification, help, and profile visually.
- Do not create placeholder routes. Deferred items have no active behavior until their features exist.
- On smaller widths, collapse secondary header controls before compromising the workflow content.

### Workflow stepper

- Render all five stages consistently on every loaded workspace screen.
- Mark the current stage with `aria-current="step"`.
- Completed, current, failed, and upcoming states have distinct icon/text treatment.
- Do not allow clicking future steps when the required evidence does not exist.

### Repository sidebar

- Empty state before context exists.
- Hierarchical tree from the bounded entries returned by the backend.
- Highlight the selected target and show test files separately when present.
- Keep **Preview Context** anchored and available after a target exists.
- Support vertical scrolling without moving the header or progress bar.
- On tablet/mobile, become a drawer opened by a clearly labelled Repository Context control.

### Main content

- Use the Stitch desktop dimensions and hierarchy as the reference, while letting dynamic content grow vertically.
- Code, logs, patches, and long paths must scroll or wrap without forcing the full page wider.
- Primary actions stay visually dominant; secondary actions use outlined treatment.
- Never insert fake test counts, durations, paths, or explanations to fill the design.

### Dialogs and disclosures

Use shadcn/Base UI primitives for accessible dialog, disclosure, tooltip, and button behavior, then restyle them with the square Verix design language. Do not let default rounded shadcn visuals leak into the final interface.

## Implementation slices

### 1. Foundation and shell

- Replace the legacy light prototype globals with Verix tokens, fonts, reset, focus treatment, and layout primitives.
- Build the header, stepper, empty repository sidebar, and responsive workspace grid.
- Render the New Verification state with no repository selected.
- Preserve existing API behavior while the visual shell is introduced.

Completion check: the initial screen closely matches the Stitch New Verification reference at its reference viewport and remains usable at tablet/mobile widths.

### 2. Context vertical slice

- Restyle the repository form and connect it to `/repository/context`.
- Render the real repository chip, pinned revision, bounded tree, target selection, and test-plan branch.
- Build the context preview dialog using `/repository/context/preview`.
- Implement Ready to Verify and Ready to Generate Tests from actual response data.

Completion check: a public Python repository can move from the empty screen to either ready state without hard-coded sample data.

### 3. Existing-test execution

- Connect Run Existing Tests to `/repository/test-run`.
- Build setup, skipped, timeout, pass, no-tests-collected, and failure result states.
- Reproduce the Stitch failure master/detail screen using real bounded output.
- Add retry, log expansion, and generate/investigate actions.

Completion check: ordinary test failures remain HTTP-success results and are rendered as evidence, not request errors.

### 4. Focused generation

- Connect Generate Focused Tests to `/repository/generate`.
- Show generated code with copy support.
- Keep existing and generated execution in separate panels/tabs with independent status.
- Handle missing Gemini configuration and unusable generated output honestly.

Completion check: a repository with no existing tests can generate and run focused tests without being treated as an error.

### 5. Investigation

- Connect `/repository/investigate`.
- Add the seven outcome presentations and bounded explanation.
- Preserve the backend classification as the source of truth.
- Make the fresh-run behavior clear before the request begins.

Completion check: every backend outcome maps to one understandable screen and recovery path.

### 6. Fix review and disposable verification

- Connect fix proposal, render the one-file unified diff, and show safety status.
- Add explicit approval and confirmation before `/repository/fix-verify`.
- Render patched-suite results and always show `github_changed: false` and disposable-workspace status.

Completion check: no patch can be verified without visible review and an explicit user action.

### 7. Polish and hardening

- Compare each implemented state with the matching Stitch PNG at the original viewport.
- Tune spacing, typography, border color, overflow, and content density.
- Verify focus order, keyboard use, screen-reader labels, reduced motion, contrast, and responsive behavior.
- Remove obsolete prototype components and styles only after their behavior is represented in the new workspace.

## Motion

Use Motion only where it clarifies state:

- a short content transition when the workspace advances stages;
- expandable logs and context panels;
- subtle progress feedback during a synchronous request.

No looping decorative animation, page-wide parallax, glow pulsing, or simulated terminal typing. Respect `prefers-reduced-motion` and keep all essential information visible without animation.

## Responsive plan

- Desktop: fixed header and progress bar, left repository sidebar, fluid main content.
- Tablet: narrower sidebar or drawer, scrollable stepper, actions allowed to wrap.
- Mobile: stacked content, repository tree in a drawer, compact repository context, horizontally scrollable code/log panels, and full-width primary actions.
- Do not shrink code or status text below a readable size merely to preserve the desktop arrangement.

## Accessibility and UX checks

- Visible keyboard focus with primary-color outline and sufficient contrast.
- Native labels for every form control.
- `aria-live` or status regions for request completion; `role="alert"` for request failures.
- No clickable `div` elements.
- Icon-only controls have accessible names.
- Disabled or deferred header items do not masquerade as working links.
- Step and test status never depend only on red/green color.
- Copy buttons report success.
- Dialog focus is trapped and returned to the trigger on close.
- Logs, diffs, and generated code are selectable text.

## Verification plan

For each implementation slice:

1. Run the frontend production/TypeScript build.
2. Run focused component or helper tests for newly introduced state logic.
3. Exercise the user-visible workflow in a browser against controlled API responses.
4. Verify at desktop, tablet, and mobile widths.
5. Compare relevant screenshots against the Stitch PNGs.
6. Run `git diff --check` before handoff.

High-value scenarios:

- invalid repository URL;
- unavailable repository or GitHub rate-limit-style failure;
- truncated repository tree;
- nested project folder;
- target change invalidating old evidence;
- existing tests pass;
- existing tests fail;
- no tests detected and no tests collected;
- dependency setup failure;
- test timeout;
- generated tests pass/fail/timeout;
- missing Gemini configuration;
- each investigation outcome;
- fix proposal rejected as not fixable;
- approved fix passes, fails, times out, or is rejected as stale/invalid;
- confirmation before clearing an active or unreviewed verification.

## Definition of frontend completion

- The real repository workflow works from connection through disposable fix verification.
- All states use real API data and no sample evidence remains in production rendering.
- Existing and generated tests are visibly and semantically separate.
- No deferred navigation leads to a fake page.
- The four provided Stitch screens are closely reproduced, with documented product corrections.
- Additional investigation, review, and verification screens follow the same design system.
- Keyboard, mobile, error, loading, empty, and reduced-motion experiences are complete.
- The production build and relevant browser checks pass.
