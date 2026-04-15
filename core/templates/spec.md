# Spec Template

Use this template to record the output of the `spec` role.
Every field is mandatory. See `core/roles/spec.md` for role constraints.

---

## Metadata

```yaml
task_id: ""              # short identifier for this task (e.g. date-slug)
request_summary: ""      # one-line restatement of the user's original request
spec_version: 1          # increment when resubmitting after reviewer rejection
```

---

## scope

> The minimal deliverable: what is in scope. Be explicit about what is NOT in scope
> to prevent downstream roles from guessing.

**In scope:**
- <!-- item -->

**Out of scope:**
- <!-- item -->

---

## constraints

> Hard limits that the implementation must not violate.
> Empty list `[]` if none beyond SEXTANT.md defaults.

- <!-- constraint: technology / compatibility / performance / time -->

---

## ambiguities

> Unresolved questions that would block downstream stages if left unaddressed.
> List them even if you have guesses — guesses belong in `open_decisions`.
> Empty list `[]` if none.

- <!-- ambiguity: what is unknown and why it matters -->

---

## acceptance

> Verifiable criteria. Each criterion must be checkable by a tool or human
> without interpretation. "Works correctly" is not an acceptance criterion.

- [ ] <!-- criterion: specific, measurable, tool-checkable -->

---

## open_decisions

> Decisions deferred to the Plan stage. For each, explain why it is deferred
> (i.e., it requires more context than the spec stage can provide).
> Empty list `[]` if none.

- <!-- decision: what needs to be decided, and why it is deferred to Plan -->
