# /sextant-verify

> **Future CLI equivalent:** `sextant verify`

Runs the Verify stage for the current task. Verify is two layers:
1. Deterministic toolchain (lint, type checks, tests)
2. Reviewer on the build diff (stage: build)

Requires Gate 3 to have passed (build summary complete, no blocking scope_creep_flags).

## Usage

```
/sextant-verify [task_id]
```

If `task_id` is not provided, look for the most recent task directory in `.sextant/traces/`.

## Workflow

1. **Gate 3 check**: verify `.sextant/traces/<task_id>/build-summary.md` exists with no
   unresolved `scope_creep_flags`. If blocked, print the unresolved flag names and:
   ```
   Gate 3 failed: unresolved scope_creep_flags in build-summary.md.
   Resolve each flag (accept / reject / defer), then run /sextant-verify again.
   ```
   Stop.

2. **Lint pre-check**: run `sextant lint <task_id>` if the CLI is installed.
   If it exits with code 1 (errors): display the lint report and stop.
   Warnings (exit 0) are displayed but do not block.
   If CLI is not installed: skip this step and note it.

3. **Determine verify commands** (in priority order):

   a. Read `verify_commands:` from `.sextant/SEXTANT.md`. If present and non-empty: use those.

   b. If not set, auto-detect from project root:
      - `package.json` found → read its `scripts` object:
        - `test` key → add `npm test`
        - `typecheck` or `type-check` key → add `npm run <key>`
        - `lint` key → add `npm run lint`
      - `pyproject.toml`, `pytest.ini`, `setup.cfg`, or `conftest.py` found → add `python -m pytest`
      - `pyproject.toml` or `setup.cfg` with `[tool.ruff]` → add `ruff check .`
      - `go.mod` found → add `go test ./...`
      - `Cargo.toml` found → add `cargo test`

      Print: "No `verify_commands` in `.sextant/SEXTANT.md`. Detected: [list]"
      Print: "Add `verify_commands:` to `.sextant/SEXTANT.md` to pin these permanently."

   c. If no commands detected: ask the user to provide them. Do not proceed until
      at least one command is confirmed.

4. **Layer 1 — Run verify commands** via Bash. Capture all output.
   Print a clear section header before each command: `── Running: <command> ──`

   If any command fails: display the failure output in full. Print:
   ```
   Layer 1 failed: <command> exited with non-zero status.
   Fix the above and run /sextant-verify again.
   ```
   Stop.

   If all pass: print `── Layer 1 passed ──` with a brief summary.

5. **Layer 2 — Reviewer** (build stage):
   Invoke `sextant-reviewer` subagent with:
   - `stage: build`
   - The build diff (read from `git diff HEAD` or recent file changes)
   - `.sextant/traces/<task_id>/build-summary.md`
   - The approved spec and plan artifacts
   - The tool output from Layer 1

   Save reviewer output to `.sextant/traces/<task_id>/review-build.md`.

6. **Validate `deletion_proposals`**: the field must be present and non-empty (even if
   `none`). If missing, the review artifact is malformed — re-invoke the reviewer
   subagent once. If still missing, stop and report.

7. **Report verdict**:
   If `rejected`: display conditions clearly. Print:
   ```
   Layer 2 failed: build reviewer rejected the diff.
   Resolve the conditions above, then run /sextant-verify again.
   ```
   Stop.

   If `approved` or `approved-with-conditions`: print `── Layer 2 passed ──`. Print:
   ```
   Verify passed. Run /sextant to close this task, or /sextant-record for explicit control.
   ```
