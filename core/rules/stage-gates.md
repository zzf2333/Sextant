# Stage Gate Rules

The Sextant flow has five fixed stages: **Spec → Plan → Build → Verify → Record**.
Each stage has a gate that must pass before the next stage begins.

## Stage Gates

### Gate 1 · Spec → Plan

**Required artifact:** completed `spec` (all fields per `core/templates/spec.md`)

**Pass criteria:** `scope` defines in/out of scope; `acceptance` has at least one verifiable
criterion; reviewer returns `approved`; all `approved-with-conditions` resolved.

**Fail action:** Return to Spec.

---

### Gate 2 · Plan → Build

**Required artifact:** completed `plan` (all fields per `core/templates/plan.md`)

**Pass criteria:** `recommended` candidate selected; `engineering_footprint` complete; L2 tasks
have concrete `rollback_path`; reviewer returns `approved`; all conditions resolved.

**Fail action:** Return to Plan.

---

### Gate 3 · Build → Verify

**Required artifact:** code diff + build summary (per `core/roles/builder.md` Outputs)

**Pass criteria:** `scope_creep_flags` resolved; all applicable `hook-registry.json` pre-build
checks passed; `footprint_delta` documents divergence from plan.

**Fail action:** Resolve flags/hooks before entering Verify.

---

### Gate 4 · Verify → Record

**Verify is two layers (both required):**
1. **Deterministic toolchain:** tests, type checks, linters, hooks — all must pass.
2. **Reviewer (build stage):** receives diff + tool results + spec + plan. Returns `approved`.

**Pass criteria:** Zero tool failures; reviewer `approved`; all conditions resolved.

**Fail action:** Fix tools first, then re-invoke reviewer.

---

### Gate 5 · Record → Done

**Required artifact:** completed `record` (per `core/templates/record.md`)

**Pass criteria:** P5 writebacks checklist answered for all four questions; either
`knowledge_writebacks` has entries or `skip_reason` is populated; knowledge files updated.

**Fail action:** Complete the checklist before closing the task.

---

## Gate Bypass Rules

Gates may only be bypassed for L0 tasks with `--force-l0` and a stated reason in the task trace.

| Gate | L0 bypass | L1 bypass | L2 bypass |
|---|---|---|---|
| Gate 1–3 | Yes, with reason | No | No |
| Gate 4–5 | No | No | No |
