# Sextant v0.1.0 Trace Contract

This document defines the minimum trace structure that `sextant lint` can verify
mechanically for v0.1.0. It does not judge review quality, implementation quality,
or whether a plan is elegant.

## Canonical Artifact Order

Trace artifacts appear in this order:

1. `spec.md`
2. `review-spec.md`
3. `plan.md`
4. `review-plan.md`
5. `build-summary.md`
6. `review-build.md`
7. `record.md`

If a later artifact exists, every earlier artifact must also exist. For example,
`record.md` means the task is closed and requires the full chain above. A task with
only `spec.md` and `review-spec.md` is still structurally valid, even if the review
verdict is `rejected`.

## Complete vs Active

A trace is complete when `record.md` exists after the full artifact chain. A trace
without `record.md` is active, blocked, or abandoned depending on the latest artifact
and review verdict.

Use:

```sh
sextant status <task_id>
sextant lint <task_id>
```

`status` explains where the task is. `lint` verifies whether the trace structure is
trustworthy enough for gates and metrics.

## Allowed Sidecar Files

The trace directory may contain:

- the seven canonical artifacts
- `rca.md`
- `usage.json`

Other files are reported as warnings because they may be scratch notes, local exports,
or accidental artifacts.

## Bypass Contract

If `spec.md` has `forced_level: true`, it must also include a non-empty
`override_reason`. This makes intentional bypasses visible in `status`, `lint`, and
release-readiness review.
