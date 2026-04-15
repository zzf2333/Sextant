#!/usr/bin/env bash
# Test: file structure, required sections, line count constraints, field coverage
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=tests/lib/helpers.sh
source "$REPO_ROOT/tests/lib/helpers.sh"

# ── 1. Required files ─────────────────────────────────────────────────

suite "Required files — core/roles"
for role in reviewer spec planner builder rca; do
    assert_file "$REPO_ROOT/core/roles/$role.md"
done

suite "Required files — core/templates"
for tmpl in review spec plan rca record; do
    assert_file "$REPO_ROOT/core/templates/$tmpl.md"
done

suite "Required files — core/rules"
for rule in task-classification stage-gates rollback; do
    assert_file "$REPO_ROOT/core/rules/$rule.md"
done

suite "Required files — core/knowledge"
for k in SEXTANT.template.md EVOLUTION.template.md \
          PROJECT_EVOLUTION_LOG.template.md hook-registry.template.json; do
    assert_file "$REPO_ROOT/core/knowledge/$k"
done

suite "Required files — adapters/claude-code/agents"
for agent in reviewer spec planner builder rca; do
    assert_file "$REPO_ROOT/adapters/claude-code/agents/sextant-$agent.md"
done

suite "Required files — adapters/claude-code/commands"
for cmd in spec plan build verify record; do
    assert_file "$REPO_ROOT/adapters/claude-code/commands/sextant-$cmd.md"
done

suite "Required files — adapters/claude-code/other"
assert_file "$REPO_ROOT/adapters/claude-code/hooks/settings.example.json"
assert_file "$REPO_ROOT/adapters/claude-code/hooks/README.md"
assert_file "$REPO_ROOT/adapters/claude-code/CLAUDE.md.snippet"
assert_file "$REPO_ROOT/adapters/claude-code/install.sh"
assert_file "$REPO_ROOT/adapters/claude-code/README.md"

suite "Required files — scripts"
assert_file "$REPO_ROOT/scripts/bootstrap.sh"

# ── 2. Role file required sections ──────────────────────────────────

suite "Role sections — all 5 roles"
for role in reviewer spec planner builder rca; do
    f="$REPO_ROOT/core/roles/$role.md"
    for section in "## Mission" "## Inputs" "## Outputs" "## Hard Constraints" "## Stop Conditions"; do
        assert_contains "$f" "$section" "$role.md: $section"
    done
done

# ── 3. Template required fields ──────────────────────────────────────

suite "Template fields — review.md"
f="$REPO_ROOT/core/templates/review.md"
assert_contains "$f" "deletion_proposals" "review.md: deletion_proposals"
assert_contains "$f" "verdict" "review.md: verdict"
assert_contains "$f" "complexity_smells" "review.md: complexity_smells"
assert_contains "$f" "verification_gaps" "review.md: verification_gaps"
assert_contains "$f" "none" "review.md: 'none' as valid value documented"

suite "Template fields — spec.md"
f="$REPO_ROOT/core/templates/spec.md"
for field in scope constraints ambiguities acceptance open_decisions; do
    assert_contains "$f" "$field" "spec.md: $field"
done

suite "Template fields — plan.md"
f="$REPO_ROOT/core/templates/plan.md"
for field in task_level candidates recommended rationale engineering_footprint rejected_alternatives; do
    assert_contains "$f" "$field" "plan.md: $field"
done

suite "Template fields — rca.md"
f="$REPO_ROOT/core/templates/rca.md"
for field in failure_evidence root_cause_layer root_cause_analysis recommended_rollback \
             prevention_hook_proposal knowledge_writebacks; do
    assert_contains "$f" "$field" "rca.md: $field"
done

suite "Template fields — record.md"
f="$REPO_ROOT/core/templates/record.md"
for field in knowledge_writebacks skip_reason; do
    assert_contains "$f" "$field" "record.md: $field"
done

# ── 4. Reviewer hard contract ─────────────────────────────────────────

suite "Reviewer contract"
f="$REPO_ROOT/core/roles/reviewer.md"
assert_contains "$f" "deletion_proposals" "reviewer.md: deletion_proposals in Hard Constraints"
assert_contains "$f" "none" "reviewer.md: 'none' as explicit option"
assert_contains "$f" "independent session" "reviewer.md: session isolation stated"
assert_contains "$f" "contract violation" "reviewer.md: missing field = contract violation"

# ── 5. deletion_proposals coverage (4 required files) ────────────────

suite "deletion_proposals coverage"
for f in \
    "core/roles/reviewer.md" \
    "core/templates/review.md" \
    "adapters/claude-code/commands/sextant-verify.md" \
    "adapters/claude-code/hooks/settings.example.json"; do
    assert_contains "$REPO_ROOT/$f" "deletion_proposals" "$f"
done

# ── 6. Subagent frontmatter ───────────────────────────────────────────

suite "Subagent frontmatter"
for agent in reviewer spec planner builder rca; do
    f="$REPO_ROOT/adapters/claude-code/agents/sextant-$agent.md"
    assert_contains "$f" "^name:" "sextant-$agent.md: name field"
    assert_contains "$f" "^model:" "sextant-$agent.md: model field"
    assert_contains "$f" "^tools:" "sextant-$agent.md: tools field"
    assert_contains "$f" "Future CLI" "sextant-$agent.md: CLI equivalent documented"
done

# ── 7. Line count constraints ─────────────────────────────────────────

suite "Line counts — roles (≤ 120)"
for f in "$REPO_ROOT"/core/roles/*.md; do
    assert_line_le "$f" 120
done

suite "Line counts — templates (≤ 80)"
for f in "$REPO_ROOT"/core/templates/*.md; do
    assert_line_le "$f" 80
done

suite "Line counts — rules (≤ 100)"
for f in "$REPO_ROOT"/core/rules/*.md; do
    assert_line_le "$f" 100
done

# ── 8. Shell script syntax ────────────────────────────────────────────

suite "Shell syntax"
assert_shell_valid "$REPO_ROOT/scripts/bootstrap.sh"
assert_shell_valid "$REPO_ROOT/adapters/claude-code/install.sh"

summary
