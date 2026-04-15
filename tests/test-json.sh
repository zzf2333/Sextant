#!/usr/bin/env bash
# Test: JSON file validity and schema checks
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=tests/lib/helpers.sh
source "$REPO_ROOT/tests/lib/helpers.sh"

# ── 1. JSON syntax ────────────────────────────────────────────────────

suite "JSON syntax"
assert_json_valid "$REPO_ROOT/core/knowledge/hook-registry.template.json"
assert_json_valid "$REPO_ROOT/adapters/claude-code/hooks/settings.example.json"

# ── 2. hook-registry.template.json schema ────────────────────────────

suite "hook-registry.template.json: required keys"
f="$REPO_ROOT/core/knowledge/hook-registry.template.json"
for key in '"hooks"' '"id"' '"trigger"' '"check_type"' \
           '"pattern_or_command"' '"error_message"' '"created_from_lesson"'; do
    assert_contains "$f" "$key" "hook-registry: $key"
done

suite "hook-registry.template.json: trigger values documented"
f="$REPO_ROOT/core/knowledge/hook-registry.template.json"
for trigger in "pre-commit" "pre-push" "pre-build" "on-stage-gate"; do
    assert_contains "$f" "$trigger" "hook-registry: trigger '$trigger' documented"
done

suite "hook-registry.template.json: check_type values documented"
f="$REPO_ROOT/core/knowledge/hook-registry.template.json"
for ctype in "regex" "file-exists" "shell"; do
    assert_contains "$f" "$ctype" "hook-registry: check_type '$ctype' documented"
done

# ── 3. settings.example.json schema ──────────────────────────────────

suite "settings.example.json: structure"
f="$REPO_ROOT/adapters/claude-code/hooks/settings.example.json"
assert_contains "$f" '"event"' "settings.example: event field"
assert_contains "$f" '"hooks"' "settings.example: hooks array"
assert_contains "$f" '"command"' "settings.example: command field"
assert_contains "$f" "deletion_proposals" "settings.example: references deletion_proposals"
assert_contains "$f" "Stop" "settings.example: Stop event hook"
assert_contains "$f" "PreToolUse" "settings.example: PreToolUse event hook"

# ── 4. Bootstrapped hook-registry.json (if present) ──────────────────

suite "project hook-registry.json (if bootstrapped)"
bootstrapped="$REPO_ROOT/hook-registry.json"
if [ -f "$bootstrapped" ]; then
    assert_json_valid "$bootstrapped"
    assert_contains "$bootstrapped" '"hooks"' "hook-registry.json: hooks key present"
else
    ok "hook-registry.json not yet bootstrapped — skipping (run scripts/bootstrap.sh to generate)"
fi

summary
