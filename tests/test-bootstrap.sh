#!/usr/bin/env bash
# Test: scripts/bootstrap.sh behavior
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=tests/lib/helpers.sh
source "$REPO_ROOT/tests/lib/helpers.sh"

# ── Setup ─────────────────────────────────────────────────────────────

TMP_TARGET="$(mktemp -d)"
cleanup() { rm -rf "$TMP_TARGET"; }
trap cleanup EXIT

# ── 1. Initial run ────────────────────────────────────────────────────

suite "bootstrap.sh: initial run exits 0"
if bash "$REPO_ROOT/scripts/bootstrap.sh" --target "$TMP_TARGET" > /tmp/sxt_bootstrap_out 2>&1; then
    ok "bootstrap.sh --target exits 0"
else
    fail "bootstrap.sh --target exited $? (output below)"
    cat /tmp/sxt_bootstrap_out
fi

suite "bootstrap.sh: creates 4 knowledge files"
assert_file "$TMP_TARGET/.sextant/SEXTANT.md"
assert_file "$TMP_TARGET/.sextant/PROJECT_EVOLUTION_LOG.md"
assert_file "$TMP_TARGET/.sextant/hook-registry.json"

suite "bootstrap.sh: creates directory layout"
assert_dir "$TMP_TARGET/modules"
assert_dir "$TMP_TARGET/.sextant/traces"
assert_file "$TMP_TARGET/.sextant/traces/.gitkeep"

# ── 2. Knowledge file content ─────────────────────────────────────────

suite "bootstrap.sh: SEXTANT.md has expected sections"
assert_contains "$TMP_TARGET/.sextant/SEXTANT.md" "Current Tech Stack"
assert_contains "$TMP_TARGET/.sextant/SEXTANT.md" "Default Preferences"
assert_contains "$TMP_TARGET/.sextant/SEXTANT.md" "Explicit Non-Goals"
assert_contains "$TMP_TARGET/.sextant/SEXTANT.md" "Known Constraints"

suite "bootstrap.sh: hook-registry.json is valid JSON"
assert_json_valid "$TMP_TARGET/.sextant/hook-registry.json"

suite "bootstrap.sh: hook-registry.json has hooks key"
assert_contains "$TMP_TARGET/.sextant/hook-registry.json" '"hooks"'

# ── 3. Idempotency ────────────────────────────────────────────────────

suite "bootstrap.sh: second run skips existing files"
run2_output=$(bash "$REPO_ROOT/scripts/bootstrap.sh" --target "$TMP_TARGET" 2>&1)
if echo "$run2_output" | grep -q "skip"; then
    ok "second run reports '[skip]' for existing files"
else
    fail "second run did not report '[skip]'"
fi

suite "bootstrap.sh: second run preserves existing file content"
echo "CUSTOM_CONTENT_MARKER" >> "$TMP_TARGET/.sextant/SEXTANT.md"
bash "$REPO_ROOT/scripts/bootstrap.sh" --target "$TMP_TARGET" > /dev/null 2>&1
assert_contains "$TMP_TARGET/.sextant/SEXTANT.md" "CUSTOM_CONTENT_MARKER" \
    "SEXTANT.md content preserved after second run"

# ── 4. Module flag ────────────────────────────────────────────────────

suite "bootstrap.sh: --module creates EVOLUTION.md"
bash "$REPO_ROOT/scripts/bootstrap.sh" --target "$TMP_TARGET" --module payments > /dev/null 2>&1
assert_dir "$TMP_TARGET/modules/payments"
assert_file "$TMP_TARGET/modules/payments/EVOLUTION.md"
assert_contains "$TMP_TARGET/modules/payments/EVOLUTION.md" "Module Purpose" \
    "EVOLUTION.md has Module Purpose section"

suite "bootstrap.sh: multiple --module flags"
bash "$REPO_ROOT/scripts/bootstrap.sh" --target "$TMP_TARGET" --module auth --module core > /dev/null 2>&1
assert_file "$TMP_TARGET/modules/auth/EVOLUTION.md"
assert_file "$TMP_TARGET/modules/core/EVOLUTION.md"

summary
