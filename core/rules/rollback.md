# Rollback Rules

Rollback is triggered when a stage gate fails and the failure cannot be resolved by continuing
forward. The goal is to return to the last known good state.

## Rollback Triggers

| Trigger | Stage | Rollback Target |
|---|---|---|
| Reviewer rejects spec | Spec | Restart Spec with user clarification |
| Reviewer rejects plan | Plan | Restart Plan (spec remains approved) |
| Scope creep flags cannot be resolved | Build | Return to Plan to amend scope |
| Deterministic tools fail | Verify | Return to Build to fix failures |
| Reviewer rejects build | Verify | Return to Build (plan remains approved) |
| Record checklist cannot be completed | Record | Investigate; do not close task |

## Rollback State Rules

1. **Only the failing stage and later stages are invalidated.** An approved spec is not invalidated
   by a plan rejection — it remains approved for the next plan attempt.

2. **A rejected artifact must be versioned.** Increment `*_version` in the artifact metadata when
   resubmitting after rejection. This preserves the audit trail.

3. **Rollback does not reset task level.** Task level only upgrades, never downgrades.
   A task classified L2 remains L2 after rollback, regardless of scope changes in the new plan.

4. **Rollback to Spec requires user involvement.** The spec role cannot unilaterally redefine scope.
   Return to the user with a specific question from `ambiguities` or a conflict statement.

## Rollback vs. Abandonment

If rollback would require more than two full cycles (Spec → Plan → Build failing twice), the task
should be flagged for RCA before the third attempt. Repeated failure on the same task indicates a
systemic issue, not just an implementation problem.

**Abandon criteria (escalate to RCA):**
- Same stage rejected three times with no substantive change between submissions
- User explicitly withdraws or redefines the task mid-flow
- A blocking external dependency (unavailable API, blocked access) makes the spec impossible

**On abandonment:** Complete a partial `record` documenting why the task was abandoned and what was
learned. Do not silently discard the task artifacts.
