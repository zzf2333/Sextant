# Record Template

Use this template at the end of every task (the Record stage).
Complete the P5 writebacks checklist before closing the task.

---

## Metadata

```yaml
task_id: ""              # must match the spec's task_id
completed_at: ""         # ISO datetime
task_level: L0 | L1 | L2
record_version: 1        # increment if record is amended after initial submission
```

---

## P5 Writebacks Checklist

Answer each question. For every "yes", create an entry in `knowledge_writebacks` below.

- [ ] Did this task change the current global technical constraints or defaults?
      → yes: update `SEXTANT.md`

- [ ] Did this task produce a design, spec, or plan lesson specific to a module?
      → yes: update `modules/<name>/EVOLUTION.md`

- [ ] Did this task produce a cross-module or project-level architectural decision?
      → yes: update `PROJECT_EVOLUTION_LOG.md`

- [ ] Did this task reveal an execution failure that a deterministic check could prevent?
      → yes: add a rule to `hook-registry.json`

---

## knowledge_writebacks

> One entry per knowledge file updated. Only include entries that will change future
> engineering judgment. If all checklist items are "no", write `skip_reason` instead.

<!-- If there are writebacks: -->
- target_file: ""
  change_type: add | update | delete
  summary: ""
  why_it_will_change_future_judgment: ""

---

## skip_reason

> If all P5 checklist items are "no", explain why no knowledge writebacks are needed.
> Do not leave this blank — an explicit "no updates needed" is better than silence.
> Delete this section if `knowledge_writebacks` has entries.

<!-- e.g.: "L0 copy change with no architectural implications; all constraints unchanged." -->
