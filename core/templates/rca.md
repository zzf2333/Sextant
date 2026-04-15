# RCA Template

Use this template to record the output of the `rca` role.
Every field is mandatory. See `core/roles/rca.md` for role constraints.
Only invoke after a confirmed failure event — not for speculative risk analysis.

---

## Metadata

```yaml
task_id: ""              # failed task's task_id or incident identifier
failure_date: ""         # ISO date when failure was observed
rca_version: 1
```

---

## failure_evidence

> What broke, error messages / stack traces (verbatim), and reproduction steps.

<!-- Evidence -->

---

## root_cause_layer

`spec` | `plan` | `build` | `verify` | `process`

> `spec`: wrong/incomplete requirement · `plan`: flawed approach · `build`: implementation deviated
> from plan · `verify`: defect not caught · `process`: workflow issue (step skipped, wrong role)

---

## root_cause_analysis

> Why the failure occurred at the identified layer. Every claim must be traceable to
> `failure_evidence` or provided artifacts. No speculation.

<!-- Analysis -->

---

## contributing_factors

> Secondary factors that amplified impact or made the failure harder to catch.
> Empty list `[]` if none.

- <!-- factor -->

---

## recommended_rollback

> Concrete steps to restore working state. Must be actionable without further investigation.

<!-- Rollback steps -->

---

## prevention_hook_proposal

> A deterministic check that would catch this failure type earlier.
> Write `none` if no mechanical check is feasible — vague suggestions go in `contributing_factors`.

`none`

---

## knowledge_writebacks

> Files to update and what to write. Only include entries that change future judgment.
> Empty list `[]` if none.

- target_file: ""
  change_type: add | update | delete
  summary: ""
  why_it_will_change_future_judgment: ""
