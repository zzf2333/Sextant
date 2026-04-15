#!/usr/bin/env bash
# Sextant test runner — runs all test-*.sh in tests/
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TESTS_DIR="$REPO_ROOT/tests"

SUITE_PASS=0
SUITE_FAIL=0
FAILED_NAMES=()

# ── Runner ────────────────────────────────────────────────────────────

run_suite() {
    local script="$1"
    local name
    name="$(basename "$script")"

    echo ""
    printf "\033[1m┌── %s\033[0m\n" "$name"

    if bash "$script"; then
        SUITE_PASS=$((SUITE_PASS + 1))
        printf "\033[1m└── \033[32mPASS\033[0m\n"
    else
        SUITE_FAIL=$((SUITE_FAIL + 1))
        FAILED_NAMES+=("$name")
        printf "\033[1m└── \033[31mFAIL\033[0m\n"
    fi
}

# ── Main ──────────────────────────────────────────────────────────────

echo ""
echo "Sextant Test Suite"
echo "══════════════════"

for test_script in "$TESTS_DIR"/test-*.sh; do
    [ -f "$test_script" ] || continue
    run_suite "$test_script"
done

echo ""
echo "══════════════════════════════════"
printf "  Suites: \033[32m%d passed\033[0m  \033[31m%d failed\033[0m\n" \
    "$SUITE_PASS" "$SUITE_FAIL"

if [ "${#FAILED_NAMES[@]}" -gt 0 ]; then
    echo "  Failed suites:"
    for name in "${FAILED_NAMES[@]}"; do
        printf "    \033[31m•\033[0m %s\n" "$name"
    done
fi
echo "══════════════════════════════════"
echo ""

[ "$SUITE_FAIL" -eq 0 ]
