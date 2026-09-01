# Verix Frontend Flows

## Purpose

This document defines what the user sees, what they can click, and how each action maps to the current backend. It describes one verification workspace with several screen states, not a collection of unrelated pages.

The frontend must keep repository code, existing-test evidence, generated-test evidence, proposed changes, and verified-fix evidence clearly separated. It must never imply that GitHub was changed or that an AI-generated test or patch is automatically correct.

## Product boundary

- Public GitHub repositories only.
- Python projects only.
- The user may select an optional branch, tag, commit, or project subdirectory.
- The user works with one selected Python source file at a time.
- Requests are synchronous. The browser must show an honest running state and must not suggest background processing.
- Workflow state lives in the browser. Refreshing the page starts a new verification because there is no account, database, or saved-run API.
- The header remains visually faithful to the Stitch design. Verifications and New Verification belong to the working flow. Explorer, Reports, Settings, notifications, and profile remain visible but do not receive fake destinations or invented functionality. Help is enabled only when useful guidance exists.
- Pasted-code generation is not part of this repository verification interface. It can remain out of the redesigned workspace until it receives a deliberate product location.

## Workspace state model

The five labels in the progress bar represent workflow stages:

1. **Context** — connect a repository, resolve its revision, inspect its bounded tree, and choose a source target.
2. **Run Tests** — run existing tests when they exist, or generate focused tests when they do not.
3. **Investigate** — collect separate existing/generated evidence and explain a classified outcome.
4. **Review Fix** — show one validated, source-only patch for explicit human review.
5. **Verify** — apply the exact approved patch in a disposable workspace and run the repository suite.

Each stage can be `upcoming`, `active`, `running`, `complete`, `warning`, or `failed`. Color cannot be the only signal: every status also needs text and an icon.

```text
New verification
  -> fetch context
  -> choose target
  -> existing tests detected?
       -> yes: ready to run existing tests
       -> no: ready to generate focused tests
  -> collect execution evidence
  -> investigate when needed
  -> propose a source fix when the outcome is fixable
  -> review and explicitly approve
  -> verify the exact patch in a disposable workspace
```

## Flow 1: Start a new verification

### Entry state

The user arrives from the header's **New Verification** control or opens the app with no active repository.

The screen shows:

- `No Repository Selected` in the repository-context area.
- Context as the active progress step; all later steps are upcoming.
- A repository URL field.
- An optional revision field for a branch, tag, or full commit SHA.
- An optional project-folder field for a nested Python project. It may sit under a compact “Repository options” disclosure so the primary form stays simple.
- A **Fetch Repository** primary action.
- A short safety note: only public GitHub repositories are supported, and fetching context does not run repository code or call Gemini.

### User actions

1. Enter a canonical URL such as `https://github.com/owner/repository`.
2. Optionally enter a revision.
3. Optionally enter a repository-relative project folder.
4. Select **Fetch Repository**.

### Frontend behavior

- Validate the obvious URL shape before sending.
- Disable only controls that would create a conflicting request while the fetch is active.
- Change the primary action to a visible loading state such as `Fetching Repository…`.
- Send `POST /repository/context` with `url`, and include `reference` and `subdirectory` only when present.
- On success, use the backend's resolved 40-character `revision` for all later actions. Do not continue using a movable branch name.
- Populate the sidebar from the returned bounded tree.
- Select `generation_selection.target_path` by default when it is present.
- Mark Context complete and move Run Tests to active.

### Failure and recovery

- HTTP 422: show the backend validation message beside the relevant form area and keep the values editable.
- HTTP 502: explain that repository context could not be fetched and offer **Retry**.
- A truncated tree is not a request failure. Show a clear “bounded tree” notice because a desired file may be outside the returned 500 entries.
- If there is no usable Python source target, explain that this repository cannot continue through focused generation and let the user choose another repository or project folder.

## Flow 2: Review context and choose the source target

After a successful context request, the app shows the shared workspace shell:

- Repository owner/name, pinned revision, and selected project folder in the header.
- The bounded repository tree in the left sidebar.
- The selected Python file highlighted.
- A target-context panel with language, selected file, related test paths, and a plain-language description when available.
- **Preview Context** in the sidebar.
- The available execution action in the main panel.

### Change target

1. The user selects another verified Python source file in the sidebar or a target selector.
2. The frontend sends `POST /repository/context` again with the pinned revision, selected subdirectory, and new `target_path`.
3. On success, replace the generation selection and clear all results that belonged to the previous target.

The target must never be accepted only because it was typed into the browser. The backend response is the source of truth that it exists, is Python, and lies inside the chosen project.

### Preview context

1. The user selects **Preview Context**.
2. The frontend sends `POST /repository/context/preview` with the pinned revision, subdirectory, and target.
3. Open a large dialog or side panel containing:
   - selected source content;
   - related existing-test files;
   - configuration files;
   - skipped paths;
   - total context bytes.
4. Explain that this is the exact bounded repository content available to Gemini if the user later chooses a Gemini action.

Previewing must not imply that code ran or that Gemini was contacted.

## Flow 3A: Existing tests were detected

This is the **Ready to Verify** state. It is selected when `test_plan.test_paths` contains existing tests.

The screen shows:

- the selected target and related test context;
- **Run Existing Tests** as the primary action;
- **Generate Focused Tests** as a secondary alternative;
- the isolation note;
- a “No Evidence Yet” panel before either action runs.

### Run existing tests

1. The user selects **Run Existing Tests**.
2. The frontend sends `POST /repository/test-run` with the public URL, pinned revision, and optional project folder.
3. Show distinct running phases: preparing repository, installing dependencies, and running tests. These are presentation phases for one synchronous request, not streamed backend events.
4. On completion, render preparation, installation, test runner, and execution evidence.

### Interpret the response

- `installation.return_code != 0` or `installation.timed_out`: setup failed. Show the setup output, do not claim tests failed, and offer retry or a different project folder.
- `execution.skipped`: tests did not run. Explain why using the returned output.
- `execution.timed_out`: show a timed-out state and preserve logs.
- `execution.return_code === 0`: show a green passed summary and allow the user to generate focused tests for deeper verification.
- `execution.return_code === 5`: treat this as “no tests collected” and move to the no-existing-tests path.
- Any other non-zero return code: show the **Test Run Found a Failure** state.

### Failure screen actions

- **View Full Logs** expands or opens the complete bounded output returned by the backend.
- **Retry Existing Tests** repeats `/repository/test-run` with the pinned selection.
- **Generate Focused Tests** calls `/repository/generate` for the selected source.
- **Investigate Failure** calls `/repository/investigate`.

Before **Investigate Failure**, explain that investigation performs a fresh generate-and-run pass for the pinned target; it does not merely reinterpret the currently displayed log.

## Flow 3B: No existing tests were detected

This is a normal product state, not an error. It can be reached because `test_plan.test_paths` is empty or because a run returns “no tests collected.”

The **Ready to Generate Tests** screen shows:

- `No Existing Tests Found` in title case;
- the selected target, Python/pytest context, and generated-test scope;
- **Generate Focused Tests** as the primary action;
- **Choose Another Target** as a real action that returns focus to target selection;
- the isolation note;
- a “No Generated Tests Yet” panel.

Do not include a working **Advanced Test Options** action until the backend accepts real generation options. If it is retained for visual parity, it must be clearly unavailable and must not pretend to save settings.

### Generate focused tests

1. The user selects **Generate Focused Tests**.
2. The frontend sends `POST /repository/generate` with the public URL, pinned revision, project folder, and selected target.
3. Show one synchronous progress state covering generation, repository preparation, installation, existing-suite execution, and generated-suite execution.
4. On success, show:
   - the exact target path;
   - generated pytest code;
   - installation evidence;
   - existing-test evidence;
   - generated-test evidence.

Existing and generated results must always be separate tabs or panels. A generated test passing must never hide an existing-suite failure, and an absent existing suite must never be presented as a passed suite.

## Flow 4: Investigate

Investigation is useful after a failure, timeout, no-tests result, or whenever the user requests a complete evidence-grounded run.

1. The user selects **Investigate Failure** or **Investigate**.
2. The frontend confirms the selected repository, pinned revision, project folder, and target.
3. Send `POST /repository/investigate`.
4. Render the returned test plan, generated code, installation result, existing result, generated result, fixed outcome, and bounded explanation.

Outcome presentation:

| Backend outcome | UI meaning | Next useful action |
| --- | --- | --- |
| `setup_failed` | Dependencies could not be prepared | View setup output, retry, or change project folder |
| `no_existing_tests` | No original suite was available | Review generated tests and their result |
| `existing_tests_timed_out` | Original suite exceeded its limit | View logs and retry if appropriate |
| `existing_tests_failed` | Original suite failed | Review evidence; propose a source fix if sufficient |
| `generated_tests_timed_out` | Focused generated suite exceeded its limit | Review generated test and logs |
| `generated_tests_failed` | Focused generated suite exposed a failure | Review evidence; propose a source fix if sufficient |
| `tests_passed` | Both applicable suites passed | Record the evidence; no fix is needed |

The explanation is supporting analysis. The backend outcome remains the authoritative classification.

## Flow 5: Review a proposed fix

Only failure or timeout outcomes with sufficient evidence can reach this stage.

1. The user selects **Propose Source Fix**.
2. Explain that this action performs a fresh investigation and asks Gemini for one source-only patch.
3. Send `POST /repository/fix-proposal` with the pinned selection and required target.
4. Show:
   - pinned revision;
   - target path;
   - short summary;
   - unified diff with added and removed lines;
   - `validated`, `approval_required`, and `applied` status in plain language;
   - a reminder that neither GitHub nor the local checkout has changed.
5. The user reviews every changed line.

Actions:

- **Back to Investigation** preserves the evidence and does not apply anything.
- **Approve and Verify in Temporary Workspace** is the only action that advances.

Approval must be explicit. Do not pre-check an approval box, auto-advance, or label the proposal as a fix before verification.

## Flow 6: Verify the approved patch

1. The user selects **Approve and Verify in Temporary Workspace** after reviewing the diff.
2. Show a final confirmation summarizing the pinned revision, one changed file, disposable application, and no GitHub write.
3. Send `POST /repository/fix-verify` with the exact proposal revision, target, patch, optional project folder, and `approved: true`.
4. Render dependency installation and patched-suite execution separately.
5. Always show the returned safety facts:
   - applied only in a disposable workspace;
   - GitHub unchanged.

Result states:

- Passed suite: green verification evidence, with wording such as “Patched suite passed in the temporary workspace.”
- Failed suite: red failure evidence; the patch was tested but not verified as passing.
- Timed out or skipped: warning/error state with exact reason and logs.

Even a passing result is evidence for human review, not proof that the change is correct.

## New Verification behavior

Selecting **New Verification** resets the browser-held workflow to the initial form. If a request is running or an unreviewed patch is visible, ask for confirmation before clearing the state. No backend deletion is required because the backend does not persist a run.

## Shared interaction rules

- Keep the pinned revision visible after context is loaded.
- Keep repository, project folder, and selected target visible on every later screen.
- Prevent conflicting requests, but do not disable unrelated reading, copying, log expansion, or context review.
- Preserve returned logs and generated code until the user changes repository, project folder, revision, or target.
- Copy controls must announce success without changing the underlying evidence.
- Errors must appear near the failed action and in an accessible alert region.
- Empty, loading, skipped, warning, failed, and passed are distinct states.
- Green means completed/passed, red means failed/error, amber means active/action/warning, and neutral charcoal means inactive structure. Every use of color also includes text or an icon.
