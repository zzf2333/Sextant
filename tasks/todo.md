# Sextant v0.1.0 First Wave — Implementation Tracker

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
