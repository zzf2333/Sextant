# /sextant

> The primary Sextant entry command. Start here for new tasks, or resume an active one.

Intelligently advances the current task to the next meaningful decision point.
Runs spec, review, and plan automatically on first invocation; then build, verify, and
record on subsequent ones. Pauses only where human judgment is actually needed.

## Usage

```
/sextant [task description]   # start a new task
/sextant                      # resume most recent active task
/sextant <task_id>            # resume a specific task by ID
```

## Design

Protocol remains intact. UX becomes simpler.

Every gate, reviewer session, and verification step still runs. This command
orchestrates them so you don't have to do it manually step by step.

**Meaningful pause points** (where the command stops and waits):

1. After plan review — you must decide whether this is the right implementation plan
2. After build — you must review scope before verification begins
3. After verify failure — reviewer or tool failures require your resolution
4. On level escalation — L2 requires explicit acknowledgment before proceeding
5. On scope creep — unresolved flags block verification
6. On durable knowledge delta — only when a writeback needs your confirmation

Everything else runs silently on the happy path.

On a happy-path L1 task the expected sequence is:

```
/sextant "task description"   → Spec + Spec Review + Plan + Plan Review  → PAUSE
/sextant                      → Build                                     → PAUSE
/sextant                      → Verify + Record fast-close                → DONE
```

---

## Workflow

### Usage capture rule

After every subagent invocation, record usage for the stage that just completed:

```bash
sextant record-usage --stage <stage> \
  --input <input_tokens> --output <output_tokens> \
  --cache-read <cache_read_tokens> --cache-creation <cache_creation_tokens> \
  --started-at <started_at> --completed-at <completed_at> \
  --model <model_id> --task-id <task_id>
```

Use actual token and timing data from the API response when available. If the CLI
is not installed, skip usage capture silently and continue the workflow. This rule
applies to `spec`, `review-spec`, `plan`, `review-plan`, `build`, `review-build`,
and `record`.

### Step 1: Resolve task context

**If a task description is provided:**

a. Generate a slug from the description (lowercase, hyphens, max 40 chars).
   Check if `.sextant/traces/<date>-<slug>/` already exists and has no `record.md`.
   If it exists and is active: **auto-resume** — proceed to Step 3 without asking.
   If it exists and is complete (has `record.md`): start a new task, append `-2` to slug.
   If it does not exist: proceed to Step 2 (start new task).

b. If the argument looks like an existing `task_id` (matches a directory name in
   `.sextant/traces/`): treat as resume, go to Step 3.

**If no argument is provided:**

c. Find all trace directories in `.sextant/traces/` that do NOT have `record.md`.
   Sort by modification time (newest first).
   If one or more found: **auto-continue the most recent one** — print one line of
   status (`task_id | stage | next action`) and proceed to Step 3.
   If none found: print "No active task. Run `/sextant <task description>` to start."
   and stop.

---

### Step 2: Start new task (Spec → Plan, then pause)

2a. **Classify task level** using `core/rules/task-classification.md`.
    Display: `Task level: <L0|L1|L2> — <reason>`

    For L2 tasks: print a one-line escalation notice and confirm before proceeding:
    "This task is L2 (high-risk). Proceeding with full gate enforcement. Continue? [y/n]"
    For L0 and L1: proceed immediately without asking.

2b. **Create trace directory**: `.sextant/traces/<task_id>/` where `task_id` is
    `<YYYY-MM-DD>-<slug>`. If the directory already exists, append `-2`, `-3`, etc.
    until the path is unique.

2c. **Load knowledge context**: read the following files if present. Skip missing files
    silently — their absence means no history yet.
    - `.sextant/SEXTANT.md`
    - `.sextant/PROJECT_EVOLUTION_LOG.md`
    - All `modules/*/EVOLUTION.md` files
    - `.sextant/hook-registry.json`

2d. **Invoke `sextant-spec` subagent** with:
    - The task description
    - The task_id and classification level
    - All knowledge files loaded in 2c

    Save output to `.sextant/traces/<task_id>/spec.md`.

2e. **Invoke `sextant-reviewer` subagent** (spec stage) with:
    - `stage: spec`
    - The spec artifact just produced

    Save output to `.sextant/traces/<task_id>/review-spec.md`.

2f. **Check spec verdict.**
    If verdict is `rejected` or `approved-with-conditions` (with unresolved conditions):
      Display the reviewer's concerns clearly. Print:
      ```
      Spec needs revision. Address the concerns above, then run `/sextant "<revised description>"`.
      ```
      Stop.

    If approved: continue.

2g. **Invoke `sextant-planner` subagent** with:
    - The approved spec artifact
    - `.sextant/SEXTANT.md`, relevant `modules/*/EVOLUTION.md`, `.sextant/hook-registry.json`

    Save output to `.sextant/traces/<task_id>/plan.md`.

2h. **Invoke `sextant-reviewer` subagent** (plan stage) with:
    - `stage: plan`
    - The plan artifact just produced

    Save output to `.sextant/traces/<task_id>/review-plan.md`.

2i. **Check plan verdict.**
    If rejected: display conditions. Print:
    ```
    Plan rejected. Address the concerns above, then run `/sextant-plan <task_id>`.
    ```
    Stop.

    If approved or approved-with-conditions: display the plan summary (candidate
    name, rationale in 2–3 lines, engineering footprint, reviewer verdict).

2j. **Pause — implementation decision point.**
    Print:
    ```
    Plan approved. Review the plan above, then run `/sextant` to build.
    ```
    Stop.

---

### Step 3: Continue from current stage

Called when resuming an active task (Step 1a or 1c).

Detect current stage by inspecting which artifacts exist in the trace directory:

**3a. Has `review-spec.md` (approved) but no `plan.md`:**
    → Run Plan + Plan Review. Go to Steps 2g–2j.

**3b. Has `review-plan.md` (approved) but no `build-summary.md`:**
    → Print: "Building: `<candidate>`…" and invoke the builder subagent.

    Invoke `sextant-builder` subagent with:
    - Approved spec artifact
    - Approved plan artifact
    - `.sextant/SEXTANT.md` and `.sextant/hook-registry.json` if present

    Save output to `.sextant/traces/<task_id>/build-summary.md`.

    Check `scope_creep_flags`. If non-empty:
      Display each flag. Print:
      ```
      Scope creep detected. For each flag, add a resolution field to build-summary.md:
        resolution: accept   → also update plan.md to include this item
        resolution: reject   → marks item as out-of-scope
        resolution: defer    → notes as future work, excluded from this build
      Then re-run `/sextant` to continue.
      ```
      Stop.

    If no blocking flags:
    ```
    Build complete. Run `/sextant` to verify, review, and record this task.
    ```
    Stop.

**3c. Has `build-summary.md` (no unresolved scope_creep_flags) but no `review-build.md`:**
    → Run Verify + Record. Go to Step 4.

**3d. Has `review-build.md` (approved) but no `record.md`:**
    → Run fast-close Record analysis. Go to Step 5.

**3e. Has `record.md`:**
    Print: "Task `<task_id>` is already complete."

**3f. Has `spec.md` but no `review-spec.md`:**
    → Spec written but not reviewed yet. Run reviewer (Steps 2e–2f).

**3g. Has `review-plan.md` with unresolved conditions or verdict `rejected`:**
    → Gate blocked. Show the rejection reason.
    Print: "Plan review failed. Run `/sextant-plan <task_id>` to re-run the planner."
    Stop.

---

### Step 4: Verify (runs from Step 3c)

4a. **Gate 3 check**: confirm `build-summary.md` has no unresolved `scope_creep_flags`.
    If blocked: print the flags and stop.

4b. **Lint pre-check**: run `sextant lint <task_id>` (if the CLI is available).
    If errors (exit code 1): display the report. Stop.
    If unavailable (CLI not installed): print "WARNING: sextant lint unavailable, skipping static checks." and continue.

4c. **Auto-detect verify commands** if `verify_commands` is not set in `.sextant/SEXTANT.md`:

    Check project root for the following signals (in order):
    - `package.json` exists → read its `scripts` field:
      - Has `test` → add `npm test`
      - Has `typecheck` or `type-check` → add `npm run typecheck` (or the exact key)
      - Has `lint` → add `npm run lint`
    - `pyproject.toml`, `pytest.ini`, `setup.cfg`, or `conftest.py` exists → add `python -m pytest`
    - `pyproject.toml` or `setup.cfg` with `[tool.ruff]` or `[tool.flake8]` → add ruff/flake8 check
    - `go.mod` exists → add `go test ./...`
    - `Cargo.toml` exists → add `cargo test`

    Print detected commands:
    "No `verify_commands` in `.sextant/SEXTANT.md`. Detected: [list]. Proceeding."

    If no commands detected: ask the user to provide them. Do not proceed until confirmed.

4d. **Run each verify command** via Bash. Capture output. If any command fails:
    Display the failure output. Print:
    ```
    Verification failed. Fix the above and run `/sextant` to retry.
    ```
    Stop.

4e. **Invoke `sextant-reviewer` subagent** with:
    - `stage: build`
    - The build diff (from `git diff HEAD` or recent file changes)
    - `build-summary.md`
    - Approved spec and plan artifacts
    - Tool output from Step 4d

    Save to `.sextant/traces/<task_id>/review-build.md`.

4f. **Verify `deletion_proposals` present**. If field is missing, the review is malformed —
    re-invoke the reviewer subagent (once). If still missing, stop and report the issue.

4g. **Check verdict**.
    If `rejected`: display conditions clearly. Print:
    ```
    Build review failed. Resolve the above and run `/sextant` to re-verify.
    ```
    Stop.

    If approved or approved-with-conditions: continue to Step 5.

---

### Step 5: Record fast-close (runs from Step 3d or after Step 4g)

5a. **Analyze for durable knowledge signals** by reading `build-summary.md` and
    scanning recent file changes:

    Signal indicators:
    - New directories created under `modules/` → likely EVOLUTION.md entry
    - Changes to `package.json`, `pyproject.toml`, `go.mod` (new dependencies) → likely `.sextant/SEXTANT.md` update
    - New entries in `.sextant/hook-registry.json` → already recorded
    - More than 2 modules touched → likely `.sextant/PROJECT_EVOLUTION_LOG.md` entry
    - Architecture-level keywords in build-summary ("redesign", "migrate", "replace",
      "new pattern", "deprecate") → likely EVOLUTION.md or `.sextant/PROJECT_EVOLUTION_LOG.md` entry

5b. **If no signals found**: create a minimal `record.md` (all P5 answers: no,
    skip_reason: "No durable changes detected.") and go to Step 5d. No knowledge
    writeback prompt is needed, but the Record artifact is still mandatory.

5c. **If signals found**:

    Print a pre-analyzed recommendation for each signal:
    ```
    Knowledge writebacks detected:
      [signal]: <description> → <target file>

    ```

    For each signal: draft the entry, show it inline, then prompt [y/n] before applying.
    On y: apply with `Edit`. On n: skip and move to next signal.

    Fill in the `record.md` artifact with the P5 checklist and writeback entries.
    Write to `.sextant/traces/<task_id>/record.md`.

5d. **Close the trace**: append to `.sextant/traces/index.md` (create if absent):
    ```
    | <task_id> | <task_level> | <completed_at> | <one-line summary> |
    ```

5e. **Print final summary**:
    ```
    Task complete: <task_id> (L<n>) — <one-line summary>
    Trace: .sextant/traces/<task_id>/
    ```

---

## Notes

- Individual stage commands (`/sextant-spec`, `/sextant-plan`, etc.) remain available for
  explicit phase control, debugging, or L2 tasks requiring step-by-step supervision.
- `/sextant-status` gives a full state dump if you need to understand where a task is.
- For L2 tasks (data model, auth, payment, sync), consider using individual stage commands
  so each gate is explicitly reviewed before proceeding.
- This command does not skip gates. Reviews still run. Knowledge writeback logic still
  applies. The difference is automation of the non-decision steps.
- A trace is not complete until `review-build.md` and `record.md` both exist after the
  full artifact chain. Build completion alone is never a closed task.
