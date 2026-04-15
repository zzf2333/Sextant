#!/usr/bin/env bash
# Sextant test helpers — source this file, do not run it directly.
# Provides assert functions and a summary reporter.

PASS=0
FAIL=0

# ── Output ──────────────────────────────────────────────────────────

suite() {
    echo ""
    echo "  ── $1"
}

ok() {
    PASS=$((PASS + 1))
    printf "    \033[32m✓\033[0m %s\n" "$1"
}

fail() {
    FAIL=$((FAIL + 1))
    printf "    \033[31m✗\033[0m FAIL: %s\n" "$1"
}

# ── Assertions ───────────────────────────────────────────────────────

assert_file() {
    local path="$1"
    local label="${2:-$path}"
    if [ -f "$path" ]; then
        ok "$label exists"
    else
        fail "missing file: $label"
    fi
}

assert_dir() {
    local path="$1"
    local label="${2:-$path}"
    if [ -d "$path" ]; then
        ok "dir $label exists"
    else
        fail "missing dir: $label"
    fi
}

assert_contains() {
    local file="$1"
    local pattern="$2"
    local desc="${3:-'$pattern' in $(basename "$file")}"
    if grep -q "$pattern" "$file" 2>/dev/null; then
        ok "$desc"
    else
        fail "$desc"
    fi
}

assert_not_contains() {
    local file="$1"
    local pattern="$2"
    local desc="${3:-no '$pattern' in $(basename "$file")}"
    if ! grep -q "$pattern" "$file" 2>/dev/null; then
        ok "$desc"
    else
        fail "$desc"
    fi
}

assert_line_le() {
    local file="$1"
    local max="$2"
    local count
    count=$(wc -l < "$file")
    local name
    name=$(basename "$file")
    if [ "$count" -le "$max" ]; then
        ok "$name: $count lines ≤ $max"
    else
        fail "$name: $count lines > $max (limit)"
    fi
}

assert_files_equal() {
    local src="$1"
    local dst="$2"
    local desc="${3:-$(basename "$src") matches source}"
    if diff -q "$src" "$dst" > /dev/null 2>&1; then
        ok "$desc"
    else
        fail "$desc"
    fi
}

assert_json_valid() {
    local file="$1"
    local label="${2:-$(basename "$file")}"
    if python3 -m json.tool "$file" > /dev/null 2>&1; then
        ok "$label: valid JSON"
    else
        fail "$label: invalid JSON"
    fi
}

assert_shell_valid() {
    local file="$1"
    local label="${2:-$(basename "$file")}"
    if bash -n "$file" 2>/dev/null; then
        ok "$label: shell syntax OK"
    else
        fail "$label: shell syntax error"
    fi
}

# ── Summary ──────────────────────────────────────────────────────────

summary() {
    local total=$((PASS + FAIL))
    echo ""
    printf "  Passed: \033[32m%d\033[0m  Failed: \033[31m%d\033[0m  Total: %d\n" \
        "$PASS" "$FAIL" "$total"
    [ "$FAIL" -eq 0 ]
}
