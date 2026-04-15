#!/usr/bin/env bash
# Test: adapters/claude-code/install.sh behavior
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=tests/lib/helpers.sh
source "$REPO_ROOT/tests/lib/helpers.sh"

# ── Setup ─────────────────────────────────────────────────────────────

TMP_PROJECT="$(mktemp -d)"
TMP_HOME="$(mktemp -d)"
cleanup() { rm -rf "$TMP_PROJECT" "$TMP_HOME"; }
trap cleanup EXIT

# ── 1. --project mode ─────────────────────────────────────────────────

suite "install.sh --project: exits 0"
if bash "$REPO_ROOT/adapters/claude-code/install.sh" \
        --project --path "$TMP_PROJECT" > /tmp/sxt_install_out 2>&1; then
    ok "install.sh --project exits 0"
else
    fail "install.sh --project exited $? (output below)"
    cat /tmp/sxt_install_out
fi

suite "install.sh --project: creates .claude directories"
assert_dir "$TMP_PROJECT/.claude/agents"
assert_dir "$TMP_PROJECT/.claude/commands"

suite "install.sh --project: deploys all 5 subagents"
for agent in reviewer spec planner builder rca; do
    assert_file "$TMP_PROJECT/.claude/agents/sextant-$agent.md"
done

suite "install.sh --project: deploys all 5 commands"
for cmd in spec plan build verify record; do
    assert_file "$TMP_PROJECT/.claude/commands/sextant-$cmd.md"
done

suite "install.sh --project: deployed files match source"
for agent in reviewer spec planner builder rca; do
    src="$REPO_ROOT/adapters/claude-code/agents/sextant-$agent.md"
    dst="$TMP_PROJECT/.claude/agents/sextant-$agent.md"
    assert_files_equal "$src" "$dst" "sextant-$agent.md matches source"
done
for cmd in spec plan build verify record; do
    src="$REPO_ROOT/adapters/claude-code/commands/sextant-$cmd.md"
    dst="$TMP_PROJECT/.claude/commands/sextant-$cmd.md"
    assert_files_equal "$src" "$dst" "sextant-$cmd.md matches source"
done

# ── 2. --user mode ────────────────────────────────────────────────────

suite "install.sh --user: deploys to HOME/.claude"
if HOME="$TMP_HOME" bash "$REPO_ROOT/adapters/claude-code/install.sh" \
        --user > /tmp/sxt_install_user_out 2>&1; then
    ok "install.sh --user exits 0"
else
    fail "install.sh --user exited $? (output below)"
    cat /tmp/sxt_install_user_out
fi
assert_dir "$TMP_HOME/.claude/agents"
assert_dir "$TMP_HOME/.claude/commands"
assert_file "$TMP_HOME/.claude/agents/sextant-reviewer.md"
assert_file "$TMP_HOME/.claude/commands/sextant-verify.md"

# ── 3. Output messages ────────────────────────────────────────────────

suite "install.sh --project: prints next-step instructions"
output=$(bash "$REPO_ROOT/adapters/claude-code/install.sh" \
             --project --path "$TMP_PROJECT" 2>&1)
if echo "$output" | grep -q "CLAUDE.md.snippet"; then
    ok "output mentions CLAUDE.md.snippet"
else
    fail "output missing CLAUDE.md.snippet reference"
fi
if echo "$output" | grep -q "bootstrap"; then
    ok "output mentions bootstrap script"
else
    fail "output missing bootstrap script reference"
fi

summary
