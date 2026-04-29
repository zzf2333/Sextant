# Sextant v0.1.0 Dogfood Gate — Version Plan

## Version Thesis

v0.1.0 should prove that Sextant is not just a set of prompts and docs, but a
repeatable Claude Code workflow that can survive real daily use.

The next version should not start the full generic LLM CLI yet. Current code is
at v0.0.8 and already has adapter commands, status/lint/metrics/tokens, usage
recording, and knowledge initialization. The missing release-quality proof is a
strict, observable dogfood loop: run real tasks, measure friction, close records,
and make failure/recovery visible enough that the author can trust the workflow.

## Product Goal

Ship `v0.1.0` as the first "closed-loop validation" release:

- Claude Code adapter is the primary supported path.
- The full Spec -> Plan -> Build -> Verify -> Record loop is easy to resume.
- Every completed task leaves enough trace evidence to audit what happened.
- Token/time/reviewer metrics are useful for deciding whether Sextant is helping
  or becoming ceremony.

## Non-Goals

- No runtime LLM calls from the Python CLI.
- No Anthropic/OpenAI/Google/Ollama backend integration yet.
- No Cursor/Cline/Gemini/Codex adapter yet.
- No new role, phase, or knowledge-file type.
- No UI beyond CLI and Claude Code commands.

## Release Scope

### 1. Trace Quality Gate

- [x] Define the minimum complete trace contract for v0.1.0.
- [x] Ensure `sextant lint` validates all required stage artifacts and common
      placeholder leaks.
- [x] Ensure closed tasks can be distinguished from active/abandoned tasks.
- [x] Add fixtures covering complete, incomplete, rejected, and bypassed traces.

### 2. Dogfood Evidence

- [x] Add a `docs/dogfood.md` report template.
- [ ] Record at least 10 real Sextant tasks before release.
- [ ] Capture 3 cases where reviewer feedback changed scope, deleted work, or
      blocked a weak plan.
- [ ] Capture at least 1 failure/recovery example that exercises RCA or rollback
      thinking.

### 3. Metrics That Decide Release Readiness

- [x] Extend `sextant metrics` or docs so release readiness can be evaluated from
      trace data.
- [x] Track closed-loop rate, reviewer deletion proposal rate, verify pass rate,
      bypass count, and average stage duration.
- [x] Document the v0.1.0 thresholds in one place.

### 4. Claude Code Adapter Polish

- [x] Audit `/sextant` resume behavior against current trace state model.
- [x] Tighten command text where users can accidentally skip Verify or Record.
- [x] Make usage-recording instructions consistent across all stage commands.
- [x] Check install output against the current `.sextant/` layout and command set.

### 5. Documentation Sync

- [x] Update `README.md` status and v0.1.0 positioning.
- [x] Update `README.zh.md` with the same release story.
- [x] Update `docs/quickstart.md` if the happy path changes.
- [x] Update `docs/roadmap.md` to reconcile current v0.0.8 reality with v0.1.0.
- [x] Update `CHANGELOG.md` under `[Unreleased]`.

## Acceptance Criteria

- [x] `make test-cli` passes.
- [x] `make test` passes or any shell-suite failure is documented with root cause.
- [x] `sextant lint` catches incomplete and malformed v0.1.0 trace fixtures.
- [ ] Dogfood report includes at least 10 real tasks and at least 3 useful reviewer
      interventions.
- [x] README, quickstart, roadmap, and changelog agree on what v0.1.0 means.

## Pending Documentation Sync List

- `README.md`: release status, supported path, next-step framing.
- `README.zh.md`: Chinese mirror of status and quickstart language.
- `docs/quickstart.md`: update only if `/sextant` flow or verification wording changes.
- `docs/roadmap.md`: align roadmap with v0.0.8 -> v0.1.0 Dogfood Gate.
- `docs/metrics.md`: add or update release-readiness metric definitions if metrics
  behavior changes.
- `CHANGELOG.md`: summarize v0.1.0 changes.
- `tasks/todo.md`: keep implementation checklist and retrospective current.

## Proposed Sequence

1. Lock trace contract and lint fixtures first.
2. Polish adapter command text around resume, verify, record, and usage capture.
3. Run dogfood tasks and collect evidence.
4. Add release-readiness metric documentation.
5. Sync docs and cut the release only after evidence is real.

## Retrospective

Planned the next version as `v0.1.0 Dogfood Gate` instead of jumping directly to
generic CLI backend work. The key decision is to prove the existing Claude Code
workflow with real trace evidence before expanding host/backend surface area.
This keeps v0.1.0 focused on trust, observability, and release discipline.

Implemented the first development slice: `sextant lint` now enforces canonical
trace artifact ordering, treats `usage.json` as an allowed sidecar, and has tests
for complete, incomplete, rejected, and bypassed traces. Added the v0.1.0 trace
contract doc, dogfood report template, release-readiness metric thresholds, and
changelog entries. Verified with `make test-cli` and `make test`.

## 2026-04-29 Completion Pass Plan

### Goal

Finish the parts of v0.1.0 that can be completed from the repository state:
adapter command consistency, release-positioning docs, and a clear remaining
dogfood gate. Do not fabricate real task evidence.

### Checklist

- [x] Audit `/sextant` and explicit stage commands for resume, Verify, Record, and usage wording.
- [x] Update command text so users cannot accidentally skip Verify or Record.
- [x] Make usage-recording instructions consistent between `/sextant` and explicit commands.
- [x] Align README, README.zh, quickstart, roadmap, and changelog with v0.1.0 Dogfood Gate.
- [x] Run focused validation and update this retrospective.
- [x] Commit the completion pass.

### Pending Documentation Sync List

- `README.md`: status should say current release is v0.0.8, next release is v0.1.0 Dogfood Gate.
- `README.zh.md`: Chinese mirror of README status and next-release positioning.
- `docs/quickstart.md`: happy path should match current `/sextant` pause wording and release-readiness note.
- `docs/roadmap.md`: v0.1.0 thresholds should match the current 10-task dogfood gate instead of the older 30-task target.
- `CHANGELOG.md`: summarize adapter/docs completion work under `[Unreleased]`.
- `tasks/todo.md`: mark completed items and record what remains blocked on real dogfood evidence.

### Retrospective

Completed the repository-side v0.1.0 completion pass. `/sextant` now has a shared
usage-capture rule for all seven measurable stages, and explicit stage commands make
clear that Build and Verify are readiness gates, not task closure. README, README.zh,
quickstart, changelog, and the internal roadmap now agree that v0.1.0 is the Dogfood
Gate release, with generic runtime LLM CLI work deferred to v0.2.

Key decision: do not fabricate dogfood evidence. The remaining release blocker is real
usage: at least 10 real tasks, 3 reviewer intervention cases, and 1 failure/recovery
case in `docs/dogfood.md`.

Verification: `make test-cli` passed with 166 tests, and `make test` passed all 6 suites.

### 2026-04-29 Corrections

- [x] Fill `docs/dogfood.md` with the current real trace inventory instead of leaving an empty template.
- [x] Promote the accumulated changelog entries from `[Unreleased]` to `[0.1.0]`.
- [x] Keep the release decision blocked because current evidence is 5 real traces, 3 closed traces, no failure/recovery case, and no recorded stage durations.
- [x] Ensure local commit messages are English before any push.

### 2026-04-29 Release Override

- [x] Maintainer requested publishing v0.1.0 despite the dogfood evidence shortfall.
- [x] Keep the shortfall explicit in `docs/dogfood.md` instead of marking unmet gates as complete.
- [x] Run release script for v0.1.0.
- [ ] Push `main` and `v0.1.0` tag.

---

# Sextant v0.1.0 First Wave — Implementation Tracker

## Current Task · Generate AGENTS.md

- [x] Inspect repository structure, commands, tests, and commit history
- [x] Create root AGENTS.md contributor guide
- [x] Verify Markdown structure and target length
- [x] Record retrospective for this task

### Retrospective

Created `AGENTS.md` as a 358-word contributor guide covering repository layout,
Make/test commands, Python style, test expectations, commit/PR conventions, and
configuration hygiene. Verified the document title, Markdown structure, and word
count. Existing unrelated working tree changes were left untouched.

## Progress

### Step 1 · core/roles/ ✓
- [x] core/roles/reviewer.md (priority)
- [x] core/roles/spec.md
- [x] core/roles/planner.md
- [x] core/roles/builder.md
- [x] core/roles/rca.md

### Step 2 · core/templates/ ✓
- [x] core/templates/review.md (priority)
- [x] core/templates/spec.md
- [x] core/templates/plan.md
- [x] core/templates/rca.md
- [x] core/templates/record.md

### Step 3 · core/rules/ ✓
- [x] core/rules/task-classification.md
- [x] core/rules/stage-gates.md
- [x] core/rules/rollback.md

### Step 4 · core/knowledge/ ✓
- [x] core/knowledge/SEXTANT.template.md
- [x] core/knowledge/EVOLUTION.template.md
- [x] core/knowledge/PROJECT_EVOLUTION_LOG.template.md
- [x] core/knowledge/hook-registry.template.json

### Step 5 · adapters/claude-code/ ✓
- [x] adapters/claude-code/agents/sextant-reviewer.md
- [x] adapters/claude-code/agents/sextant-spec.md
- [x] adapters/claude-code/agents/sextant-planner.md
- [x] adapters/claude-code/agents/sextant-builder.md
- [x] adapters/claude-code/agents/sextant-rca.md
- [x] adapters/claude-code/commands/sextant-spec.md
- [x] adapters/claude-code/commands/sextant-plan.md
- [x] adapters/claude-code/commands/sextant-build.md
- [x] adapters/claude-code/commands/sextant-verify.md
- [x] adapters/claude-code/commands/sextant-record.md
- [x] adapters/claude-code/hooks/settings.example.json
- [x] adapters/claude-code/hooks/README.md
- [x] adapters/claude-code/CLAUDE.md.snippet
- [x] adapters/claude-code/install.sh
- [x] adapters/claude-code/README.md

### Step 6 · scripts/ ✓
- [x] scripts/bootstrap.sh

### Step 7 · README ✓
- [x] README.md (add Quick Start with Claude Code)
- [x] README.zh.md (sync)

## Verification Checklist ✓
- [x] `grep -r "deletion_proposals"` hits: reviewer.md / templates/review.md / commands/sextant-verify.md / hooks/settings.example.json
- [x] JSON syntax: hook-registry.template.json + hooks/settings.example.json
- [x] Shell syntax: scripts/bootstrap.sh + adapters/claude-code/install.sh
- [x] Line count: roles ≤ 120 / templates ≤ 80 / rules ≤ 100 (all pass)
- [ ] Dogfood: full Spec→Plan→Build→Verify→Record cycle on a real L0 task (needs a separate session with adapter installed)

## Retrospective

**Completed:** 2026-04-15

**What was built:**
- 33 files across core/ + adapters/ + scripts/
- scripts work: bootstrap.sh creates 4 knowledge files, install.sh deploys agents+commands to .claude/
- All formal checks pass

**Prompt length discipline worked well:** The 120/80/100-line caps forced precision. Two files
(plan.md at 84, rca.md at 96) exceeded template limits and were immediately trimmed — the cap
caught the bloat.

**One deferred item:** The dogfood cycle (full Spec→Plan→Build→Verify→Record on a real L0 task)
requires a new Claude Code session with the adapter installed. This is the next step before
the implementation can be called truly complete per the plan's "completion criteria."

**Pending for next session:** Fill in the Sextant project's own SEXTANT.md with Sextant's
own tech stack, defaults, and non-goals (currently bootstrapped as a template).
