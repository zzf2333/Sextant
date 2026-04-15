# Plan Template

Use this template to record the output of the `planner` role.
Every field is mandatory. See `core/roles/planner.md` for role constraints.

---

## Metadata

```yaml
task_id: ""              # must match the spec's task_id
spec_ref: ""             # path or identifier of the approved spec
plan_version: 1          # increment when resubmitting after reviewer rejection
task_level: L0 | L1 | L2
```

---

## candidates

> 1–2 approaches maximum. Each candidate must be self-contained for a reviewer to evaluate.

### Candidate A: <!-- name -->

<!-- Brief description -->

**Pros:** <!-- pro -->
**Cons:** <!-- con -->

---

## recommended

`Candidate A`

---

## rationale

> Why this is the most economical path right now. Reference boring defaults and current
> requirements — not hypothetical future flexibility.

<!-- Rationale -->

---

## engineering_footprint

```yaml
new_files:
  - # path and purpose

new_dependencies:
  - # package and why existing options don't suffice; [] if none

affected_modules:
  - # module name and how it is affected

rollback_path: >
  # L2: concrete revert sequence. L0/L1: brief undo note.
```

---

## rejected_alternatives

> Prevents re-exploring dead ends. Empty list `[]` if none.

- <!-- alternative and reason for rejection -->
