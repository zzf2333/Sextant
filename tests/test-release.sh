#!/usr/bin/env bash
# Test: Release tooling — VERSION file, CHANGELOG, scripts, and CI workflows
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=tests/lib/helpers.sh
source "$REPO_ROOT/tests/lib/helpers.sh"

VERSION_FILE="$REPO_ROOT/VERSION"
CHANGELOG="$REPO_ROOT/CHANGELOG.md"

# ── 1. VERSION file ───────────────────────────────────────────────────

suite "VERSION file"
assert_file "$VERSION_FILE" "VERSION exists"

# Validate format: X.Y.Z (digits only)
suite "VERSION format"
if [ -f "$VERSION_FILE" ]; then
    VERSION="$(cat "$VERSION_FILE" | tr -d '[:space:]')"
    if printf '%s' "$VERSION" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+$'; then
        ok "VERSION format is valid semver ($VERSION)"
    else
        fail "VERSION format invalid: '$VERSION' (expected X.Y.Z)"
    fi
fi

# ── 2. CHANGELOG.md ───────────────────────────────────────────────────

suite "CHANGELOG.md structure"
assert_file "$CHANGELOG" "CHANGELOG.md exists"
assert_contains "$CHANGELOG" "## \[Unreleased\]"   "CHANGELOG: [Unreleased] section"
assert_contains "$CHANGELOG" "Keep a Changelog"    "CHANGELOG: format attribution"
assert_contains "$CHANGELOG" "Semantic Versioning" "CHANGELOG: semver reference"

suite "CHANGELOG.md: current version section"
if [ -f "$VERSION_FILE" ] && [ -f "$CHANGELOG" ]; then
    VERSION="$(cat "$VERSION_FILE" | tr -d '[:space:]')"
    if grep -q "## \[$VERSION\]" "$CHANGELOG"; then
        ok "CHANGELOG: section ## [$VERSION] exists"
        # Check it has content
        SECTION=$(awk -v ver="$VERSION" '
            /^## \[/ { if (found) exit; if (index($0, "[" ver "]") > 0) found=1; next }
            found { print }
        ' "$CHANGELOG")
        if [ -n "$(printf '%s' "$SECTION" | tr -d '[:space:]')" ]; then
            ok "CHANGELOG: [$VERSION] section has content"
        else
            fail "CHANGELOG: [$VERSION] section is empty"
        fi
    else
        fail "CHANGELOG: missing section ## [$VERSION]"
    fi
fi

# ── 3. Version consistency across docs ────────────────────────────────

suite "Version consistency"
if [ -f "$VERSION_FILE" ]; then
    VERSION="$(cat "$VERSION_FILE" | tr -d '[:space:]')"
    assert_contains "$REPO_ROOT/README.md"    "v$VERSION" "README.md: v$VERSION referenced"
    assert_contains "$REPO_ROOT/README.zh.md" "v$VERSION" "README.zh.md: v$VERSION referenced"
fi

# ── 4. Release scripts ────────────────────────────────────────────────

suite "scripts/bump-version.sh"
assert_file "$REPO_ROOT/scripts/bump-version.sh" "bump-version.sh exists"
assert_shell_valid "$REPO_ROOT/scripts/bump-version.sh" "bump-version.sh"

suite "scripts/bump-version.sh --dry-run"
if [ -f "$REPO_ROOT/scripts/bump-version.sh" ]; then
    RESULT="$(sh "$REPO_ROOT/scripts/bump-version.sh" --dry-run --bump patch 2>/dev/null)"
    VERSION="$(cat "$VERSION_FILE" | tr -d '[:space:]')"
    MAJOR="$(printf '%s' "$VERSION" | cut -d. -f1)"
    MINOR="$(printf '%s' "$VERSION" | cut -d. -f2)"
    PATCH="$(printf '%s' "$VERSION" | cut -d. -f3)"
    EXPECTED="$MAJOR.$MINOR.$((PATCH + 1))"
    if [ "$RESULT" = "$EXPECTED" ]; then
        ok "bump-version.sh --bump patch outputs correct version ($RESULT)"
    else
        fail "bump-version.sh --bump patch: expected '$EXPECTED', got '$RESULT'"
    fi
fi

suite "scripts/release.sh"
assert_file "$REPO_ROOT/scripts/release.sh" "release.sh exists"
assert_shell_valid "$REPO_ROOT/scripts/release.sh" "release.sh"

# ── 5. GitHub Actions workflows ───────────────────────────────────────

suite "GitHub Actions: ci.yml"
assert_file "$REPO_ROOT/.github/workflows/ci.yml" "ci.yml exists"
assert_contains "$REPO_ROOT/.github/workflows/ci.yml" "make test"      "ci.yml: runs make test"
assert_contains "$REPO_ROOT/.github/workflows/ci.yml" "pull_request"   "ci.yml: triggers on pull_request"
assert_contains "$REPO_ROOT/.github/workflows/ci.yml" "ubuntu-latest"  "ci.yml: runs on ubuntu-latest"

suite "GitHub Actions: release.yml"
assert_file "$REPO_ROOT/.github/workflows/release.yml" "release.yml exists"
assert_contains "$REPO_ROOT/.github/workflows/release.yml" "make test"          "release.yml: runs make test"
assert_contains "$REPO_ROOT/.github/workflows/release.yml" "v*.*.*"             "release.yml: tag pattern"
assert_contains "$REPO_ROOT/.github/workflows/release.yml" "contents: write"    "release.yml: write permission"
assert_contains "$REPO_ROOT/.github/workflows/release.yml" "action-gh-release"  "release.yml: uses gh-release action"
assert_contains "$REPO_ROOT/.github/workflows/release.yml" "CHANGELOG.md"       "release.yml: reads CHANGELOG"

suite "GitHub Actions: PR template"
assert_file "$REPO_ROOT/.github/pull_request_template.md" "pull_request_template.md exists"
assert_contains "$REPO_ROOT/.github/pull_request_template.md" "make test"   "PR template: make test checkbox"
assert_contains "$REPO_ROOT/.github/pull_request_template.md" "Changelog"   "PR template: Changelog section"

summary
