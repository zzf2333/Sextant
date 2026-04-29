# Sextant v0.1.0 Dogfood Report

Use this file to decide whether v0.1.0 is ready to release. Fill it from real
Sextant tasks only; do not include synthetic fixtures or documentation-only dry runs.

## Release Thresholds

| Signal | v0.1.0 threshold | Source |
|---|---:|---|
| Real tasks recorded | >= 10 | `.sextant/traces/` |
| Closed-loop completion rate | >= 80% | `record.md` present after full trace chain |
| Reviewer non-empty deletion proposal rate | >= 50% | `sextant metrics --since 30` |
| Verify first-pass rate | >= 60% | dogfood task table |
| Active bypass rate | <= 20% | `forced_level: true` / skip markers |
| Average stage duration | <= 90 seconds | `sextant tokens --since 30` |

## Task Table

| Task ID | Level | Closed | Verify first pass | Reviewer changed outcome | Bypass | Notes |
|---|---|---|---|---|---|---|
| 2026-04-20-v006-init-command | L1 | yes | yes | yes | no | Closed trace for `/sextant-init`; reviewer tightened plan scope and detection behavior. |
| 2026-04-20-knowledge-files-to-sextant-dir | L1 | yes | yes | yes | no | Closed trace for moving knowledge files under `.sextant/`. |
| 2026-04-20-token-consumption-stats | L1 | yes | yes | yes | no | Closed trace for `sextant tokens`; reviewer changes affected spec, plan, and build. |
| 2026-04-20-sextant-happy-path | L1 | no | n/a | yes | no | Active trace stopped after plan review; no build, verify, or record artifact yet. |
| 2026-04-20-v004-polish-release | L1 | no | n/a | yes | no | Active trace stopped after build summary; missing build review and record. |

Current count: 5 real traces, 3 closed traces. This is below the v0.1.0 threshold
of 10 real tasks and below the 80% closed-loop completion threshold.

## Reviewer Intervention Cases

Record at least 3 cases where reviewer output changed the task:

| Task ID | Stage | Reviewer finding | What changed |
|---|---|---|---|
| 2026-04-20-v006-init-command | plan | Remove Java/Kotlin detection and bound `--force` behavior. | Plan scope narrowed to the documented manifest set; `--force` limited to the four knowledge files. |
| 2026-04-20-token-consumption-stats | spec | Remove duplicated scope/constraint/acceptance items and clarify `--detail` semantics. | Spec v2 removed redundant items, clarified `--task-id` vs `--detail`, and added fixture/performance acceptance criteria. |
| 2026-04-20-token-consumption-stats | plan | Remove `cli/parsers.py` from affected modules and add direct tests for stage input rules. | Plan stopped listing a no-op file and added `TestStageInputRules` coverage instead. |
| 2026-04-20-token-consumption-stats | build | Remove unused `TokenSummary.completed_at` / `task_level` and trim duplicated docstring content. | Build deleted unused parsed fields and reduced module-level duplication. |

## Failure / Recovery Case

Record at least 1 failure that exercised RCA, rollback thinking, or a concrete
recovery path:

| Task ID | Failure | Root cause | Recovery | Follow-up |
|---|---|---|---|---|
| pending | No qualifying failure/recovery case recorded yet. | n/a | n/a | Capture at least one real failure that exercises RCA, rollback thinking, or a concrete recovery path before release. |

## Release Decision

- [ ] At least 10 real tasks recorded
- [ ] Trace lint passes for completed tasks
- [ ] Thresholds above are met or failures have explicit root-cause notes
- [ ] README, quickstart, roadmap, metrics, changelog, and this report agree

Decision: Release v0.1.0 with maintainer override.

Rationale: Current dogfood evidence has 5 real traces, 3 closed traces, no recorded
failure/recovery case, and no recorded stage duration data. The release is cut as the
v0.1.0 Dogfood Gate tooling release by explicit maintainer override, with the evidence
shortfall preserved here as the first post-release dogfood target.
