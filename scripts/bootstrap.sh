#!/usr/bin/env sh
# Sextant bootstrap script
# Initializes the four Sextant knowledge files in an existing project.
#
# Usage:
#   ./scripts/bootstrap.sh [--target <path>] [--module <name>]
#
#   --target <path>   Project root to bootstrap (default: current directory)
#   --module <name>   Also create modules/<name>/EVOLUTION.md (can repeat)

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
KNOWLEDGE_DIR="$SCRIPT_DIR/../core/knowledge"

TARGET="$(pwd)"
MODULES=""

# Parse arguments
while [ "$#" -gt 0 ]; do
    case "$1" in
        --target) TARGET="$2"; shift 2 ;;
        --module) MODULES="$MODULES $2"; shift 2 ;;
        *) echo "Unknown option: $1"; echo "Usage: $0 [--target <path>] [--module <name>]"; exit 1 ;;
    esac
done

echo "Bootstrapping Sextant knowledge layout in: $TARGET"
echo ""

# Helper: copy template if destination does not exist
copy_if_absent() {
    src="$1"
    dst="$2"
    if [ -f "$dst" ]; then
        echo "  [skip] $dst already exists"
    else
        cp "$src" "$dst"
        echo "  [created] $dst"
    fi
}

# 1. SEXTANT.md
copy_if_absent \
    "$KNOWLEDGE_DIR/SEXTANT.template.md" \
    "$TARGET/SEXTANT.md"

# 2. PROJECT_EVOLUTION_LOG.md
copy_if_absent \
    "$KNOWLEDGE_DIR/PROJECT_EVOLUTION_LOG.template.md" \
    "$TARGET/PROJECT_EVOLUTION_LOG.md"

# 3. hook-registry.json
copy_if_absent \
    "$KNOWLEDGE_DIR/hook-registry.template.json" \
    "$TARGET/hook-registry.json"

# 4. modules/ directory
if [ ! -d "$TARGET/modules" ]; then
    mkdir -p "$TARGET/modules"
    echo "  [created] $TARGET/modules/"
else
    echo "  [skip] $TARGET/modules/ already exists"
fi

# 5. Per-module EVOLUTION.md (if --module specified)
for mod in $MODULES; do
    mod_dir="$TARGET/modules/$mod"
    mkdir -p "$mod_dir"
    copy_if_absent \
        "$KNOWLEDGE_DIR/EVOLUTION.template.md" \
        "$mod_dir/EVOLUTION.md"
done

# 6. .sextant/traces/ trace directory
if [ ! -d "$TARGET/.sextant/traces" ]; then
    mkdir -p "$TARGET/.sextant/traces"
    touch "$TARGET/.sextant/traces/.gitkeep"
    echo "  [created] $TARGET/.sextant/traces/ (.gitkeep)"
else
    echo "  [skip] $TARGET/.sextant/traces/ already exists"
fi

echo ""
echo "Bootstrap complete."
echo ""
echo "Next steps:"
echo "  1. Edit SEXTANT.md — fill in your tech stack, defaults, and non-goals."
echo "  2. For each module, run:"
echo "       $0 --target $TARGET --module <module-name>"
echo "  3. Install the Claude Code adapter:"
echo "       $SCRIPT_DIR/../adapters/claude-code/install.sh --project --path $TARGET"
