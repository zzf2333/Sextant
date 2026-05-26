# Task Contract Template

Use this template to define the contract for a single executable task.
Every field is mandatory. The Executor receives only this contract and
the worktree — no additional context.

---

## Metadata

```yaml
task_id: ""              # unique task identifier
task_type: ""            # foundation | implementation | integration
depends_on: []           # list of task_ids this task depends on
parallelizable: false    # can this task run in parallel with siblings?
independent_verification: true  # can this task verify independently?
```

---

## objective

> One-line description of what to build. Must be unambiguous.

<!-- e.g., "Implement Runtime Worker Scheduler" -->

---

## allowed_paths

> File/directory globs the Worker may modify. Only these paths.
> Use `**` for recursive matching.

```yaml
allowed_paths: []
# Example:
# - src/runtime/**
# - tests/runtime/**
```

---

## forbidden_paths

> File/directory globs the Worker must never touch.
> These override allowed_paths on conflict.

```yaml
forbidden_paths: []
# Example:
# - src/ui/**
# - package.json
# - db/**
```

---

## constraints

> Hard limits that the implementation must respect.
> Contract violations are treated as build failures.

- <!-- constraint -->
<!-- Example:
- Do not modify public API signatures
- Do not add new npm dependencies
- Must maintain backward compatibility with v1 config format
-->

---

## dependencies

> External dependencies required for this task.
> Empty list `[]` if none beyond existing project deps.

```yaml
dependencies: []
# Example:
# - name: reasonix
#   version: ">=0.1.0"
```

---

## acceptance

> Verifiable acceptance criteria. Each criterion must map to a
> deterministic command or check. No "works correctly" criteria.

- [ ] <!-- criterion: specific command or check -->
<!-- Example:
- [ ] npm run test -- tests/runtime
- [ ] npm run lint
- [ ] TypeScript strict mode passes
-->

---

## review_focus

> Areas the Reviewer should scrutinize most carefully.
> These are hints, not constraints — the Reviewer may check anything.

- <!-- focus area -->
<!-- Example:
- race conditions in Worker lifecycle
- memory leaks in long-running scheduler
- error handling for Worker crash scenarios
-->
