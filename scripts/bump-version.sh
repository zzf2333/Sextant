#!/usr/bin/env sh
# Sextant version bump utility
# Computes and applies a version bump to VERSION + README files.
# Outputs the new version number to stdout; all other messages go to stderr.
#
# Usage:
#   ./scripts/bump-version.sh [--dry-run] (--bump patch|minor|major | --set <version>)

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VERSION_FILE="$REPO_ROOT/VERSION"

usage() {
    echo "Usage: bump-version.sh [--dry-run] (--bump patch|minor|major | --set <version>)" >&2
    echo "" >&2
    echo "  --bump patch    0.1.0 → 0.1.1" >&2
    echo "  --bump minor    0.1.0 → 0.2.0" >&2
    echo "  --bump major    0.1.0 → 1.0.0" >&2
    echo "  --set <ver>     Set exact version (e.g. 0.1.0)" >&2
    echo "  --dry-run       Print changes without applying them" >&2
    exit 1
}

DRY_RUN=0
BUMP_TYPE=""
SET_VERSION=""

while [ "$#" -gt 0 ]; do
    case "$1" in
        --dry-run) DRY_RUN=1 ;;
        --bump)    shift; BUMP_TYPE="$1" ;;
        --set)     shift; SET_VERSION="$1" ;;
        *) echo "Unknown option: $1" >&2; usage ;;
    esac
    shift
done

if [ -z "$BUMP_TYPE" ] && [ -z "$SET_VERSION" ]; then
    usage
fi

# ── Compute new version ───────────────────────────────────────────────

CURRENT="$(cat "$VERSION_FILE")"
MAJOR="$(printf '%s' "$CURRENT" | cut -d. -f1)"
MINOR="$(printf '%s' "$CURRENT" | cut -d. -f2)"
PATCH="$(printf '%s' "$CURRENT" | cut -d. -f3)"

if [ -n "$SET_VERSION" ]; then
    NEW="$SET_VERSION"
elif [ "$BUMP_TYPE" = "patch" ]; then
    NEW="$MAJOR.$MINOR.$((PATCH + 1))"
elif [ "$BUMP_TYPE" = "minor" ]; then
    NEW="$MAJOR.$((MINOR + 1)).0"
elif [ "$BUMP_TYPE" = "major" ]; then
    NEW="$((MAJOR + 1)).0.0"
else
    echo "Unknown bump type: $BUMP_TYPE" >&2; usage
fi

# stdout: new version (captured by release.sh)
printf '%s\n' "$NEW"

echo "  $CURRENT → $NEW" >&2

if [ "$DRY_RUN" = "1" ]; then
    echo "  [dry-run] Would update: VERSION, README.md, README.zh.md" >&2
    exit 0
fi

# ── Apply ─────────────────────────────────────────────────────────────

printf '%s\n' "$NEW" > "$VERSION_FILE"
echo "  [updated] VERSION" >&2

# Replace version string in a file (portable — avoids sed -i '' vs sed -i differences)
replace_in_file() {
    local file="$1"
    local old_pat="$2"
    local new_pat="$3"
    if [ ! -f "$file" ]; then
        echo "  [skip]    $(basename "$file") (not found)" >&2
        return
    fi
    if grep -qF "$old_pat" "$file"; then
        tmp="$(mktemp)"
        sed "s/$old_pat/$new_pat/g" "$file" > "$tmp" && mv "$tmp" "$file"
        echo "  [updated] $(basename "$file")" >&2
    else
        echo "  [skip]    $(basename "$file") (pattern not found)" >&2
    fi
}

replace_in_file "$REPO_ROOT/README.md"    "v$CURRENT" "v$NEW"
replace_in_file "$REPO_ROOT/README.zh.md" "v$CURRENT" "v$NEW"
