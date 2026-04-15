#!/usr/bin/env sh
# Sextant release script
# Orchestrates a version bump, CHANGELOG check, commit, and tag.
# Does NOT push to remote — prints the push command for manual execution.
#
# Usage:
#   ./scripts/release.sh [--dry-run] (--bump patch|minor|major | --set <version>)

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VERSION_FILE="$REPO_ROOT/VERSION"
CHANGELOG="$REPO_ROOT/CHANGELOG.md"

usage() {
    echo "Usage: release.sh [--dry-run] (--bump patch|minor|major | --set <version>)" >&2
    echo "" >&2
    echo "  --bump patch    Increment patch version (0.1.0 → 0.1.1)" >&2
    echo "  --bump minor    Increment minor version (0.1.0 → 0.2.0)" >&2
    echo "  --bump major    Increment major version (0.1.0 → 1.0.0)" >&2
    echo "  --set <ver>     Set exact version (e.g. 0.1.0)" >&2
    echo "  --dry-run       Print all actions without executing them" >&2
    exit 1
}

DRY_RUN=0
BUMP_ARGS=""

while [ "$#" -gt 0 ]; do
    case "$1" in
        --dry-run) DRY_RUN=1; BUMP_ARGS="$BUMP_ARGS --dry-run" ;;
        --bump)    shift; BUMP_ARGS="$BUMP_ARGS --bump $1" ;;
        --set)     shift; BUMP_ARGS="$BUMP_ARGS --set $1" ;;
        *) echo "Unknown option: $1" >&2; usage ;;
    esac
    shift
done

if [ -z "$BUMP_ARGS" ] && [ "$DRY_RUN" = "0" ]; then
    usage
fi
# If only --dry-run was given without a bump type, that's not useful
if [ "$BUMP_ARGS" = " --dry-run" ]; then
    usage
fi

step() { echo ""; echo "── $1"; }

# ── Preflight ────────────────────────────────────────────────────────

step "Preflight checks"

CURRENT="$(cat "$VERSION_FILE")"
echo "  Current version: v$CURRENT"

if [ "$DRY_RUN" = "0" ]; then
    # Working tree must be clean
    if [ -n "$(git -C "$REPO_ROOT" status --porcelain)" ]; then
        echo "  [abort] Working tree is dirty. Commit or stash changes first."
        exit 1
    fi
    echo "  ✓ Working tree clean"

    # Must be on main
    BRANCH="$(git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD)"
    if [ "$BRANCH" != "main" ]; then
        echo "  [abort] Must be on 'main' branch (currently '$BRANCH')"
        exit 1
    fi
    echo "  ✓ On 'main' branch"
fi

# ── Tests ─────────────────────────────────────────────────────────────

step "Running tests"
if [ "$DRY_RUN" = "1" ]; then
    echo "  [dry-run] Would run: make test"
else
    make -C "$REPO_ROOT" test
fi

# ── Version bump ──────────────────────────────────────────────────────

step "Bumping version"
# shellcheck disable=SC2086
NEW_VERSION="$("$SCRIPT_DIR/bump-version.sh" $BUMP_ARGS)"

# ── CHANGELOG check ───────────────────────────────────────────────────

step "Checking CHANGELOG.md"
if grep -q "## \[$NEW_VERSION\]" "$CHANGELOG"; then
    # Verify the section has actual content (not empty)
    SECTION=$(awk -v ver="$NEW_VERSION" '
        /^## \[/ { if (found) exit; if (index($0, "[" ver "]") > 0) found=1; next }
        found { print }
    ' "$CHANGELOG")
    if [ -z "$(printf '%s' "$SECTION" | tr -d '[:space:]')" ]; then
        echo "  [abort] CHANGELOG.md has a [$NEW_VERSION] section but it is empty."
        echo "  Fill in the release notes before running release."
        exit 1
    fi
    echo "  ✓ CHANGELOG.md has non-empty [$NEW_VERSION] section"
else
    echo "  [abort] CHANGELOG.md missing section: ## [$NEW_VERSION]"
    echo "  Add the release notes under [Unreleased], then rename to [$NEW_VERSION] - YYYY-MM-DD"
    exit 1
fi

# ── Commit + tag ──────────────────────────────────────────────────────

step "Creating release commit and tag"
if [ "$DRY_RUN" = "1" ]; then
    echo "  [dry-run] Would run: git add VERSION README.md README.zh.md CHANGELOG.md"
    echo "  [dry-run] Would run: git commit -m 'chore: release v$NEW_VERSION'"
    echo "  [dry-run] Would run: git tag -a 'v$NEW_VERSION' -m 'Release v$NEW_VERSION'"
else
    git -C "$REPO_ROOT" add \
        "$VERSION_FILE" \
        "$REPO_ROOT/README.md" \
        "$REPO_ROOT/README.zh.md" \
        "$CHANGELOG"
    git -C "$REPO_ROOT" commit -m "chore: release v$NEW_VERSION"
    git -C "$REPO_ROOT" tag -a "v$NEW_VERSION" -m "Release v$NEW_VERSION"
    echo "  ✓ Committed and tagged v$NEW_VERSION"
fi

# ── Next steps ────────────────────────────────────────────────────────

echo ""
echo "══════════════════════════════════════"
echo "  Release v$NEW_VERSION ready."
echo ""
echo "  Next steps (manual — review before running):"
echo "    git push origin main"
echo "    git push origin v$NEW_VERSION"
echo ""
echo "  Pushing the tag triggers the GitHub Release workflow."
echo "══════════════════════════════════════"
