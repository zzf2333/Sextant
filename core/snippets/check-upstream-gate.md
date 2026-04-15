# Upstream Gate Check

Shared procedure for verifying that an upstream reviewer-approved artifact exists before
proceeding to the next stage. Reference this snippet from adapter commands instead of
duplicating gate logic locally.

## Parameters

When citing this snippet, pass:

- `stage`: the upstream stage name — one of `spec`, `plan`, or `build`
- `task_id`: the current task identifier (resolved from command argument or latest trace)

## Procedure

1. Resolve the artifact path:
   ```
   .sextant/traces/<task_id>/review-<stage>.md
   ```

2. **Existence check**: If the file does not exist:
   - Print: `Gate check failed: .sextant/traces/<task_id>/review-<stage>.md not found.`
   - Stop. Do not proceed to the next stage.

3. **Parse `verdict`**: Read the `verdict` field from the file's yaml frontmatter block.

4. **Accept conditions**:
   - `approved` → proceed.
   - `approved-with-conditions` → proceed **only if** all items in the `conditions` section
     are explicitly marked as resolved (prefixed with `[resolved]` or the conditions list is
     empty). If any condition is unresolved, treat the same as `rejected`.

5. **Reject conditions**: If verdict is `rejected`, `changes-requested`, or
   `approved-with-conditions` with unresolved conditions:
   - Print: `Gate check failed: review-<stage>.md has verdict '<value>'.`
   - If `approved-with-conditions`, list each unresolved condition.
   - Stop. Do not proceed to the next stage.

## What this check does NOT do

- Does not evaluate whether the review was thorough or the proposals were high-quality.
- Does not re-run the reviewer subagent.
- Does not check `deletion_proposals` completeness — that is `sextant lint`'s responsibility.
- Does not apply to Gate 3 (build → verify), which checks `scope_creep_flags` in
  `build-summary.md`, not a reviewer verdict.
