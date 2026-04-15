#!/usr/bin/env sh
# Sextant Claude Code adapter installer
# Installs sextant-* subagents and slash commands into a Claude Code context.
#
# Usage:
#   ./install.sh --user              # install to ~/.claude/ (all projects)
#   ./install.sh --project           # install to ./.claude/ (this project only)
#   ./install.sh --project --path /path/to/project  # install to a specific project

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
AGENTS_SRC="$SCRIPT_DIR/agents"
COMMANDS_SRC="$SCRIPT_DIR/commands"

usage() {
    echo "Usage: $0 --user | --project [--path <project_path>]"
    echo ""
    echo "  --user              Install to ~/.claude/ (applies to all projects)"
    echo "  --project           Install to ./.claude/ (current project only)"
    echo "  --path <path>       Use <path> as project root (with --project)"
    exit 1
}

# Parse arguments
TARGET=""
PROJECT_PATH="$(pwd)"

while [ "$#" -gt 0 ]; do
    case "$1" in
        --user)    TARGET="user"; shift ;;
        --project) TARGET="project"; shift ;;
        --path)    PROJECT_PATH="$2"; shift 2 ;;
        *)         usage ;;
    esac
done

[ -z "$TARGET" ] && usage

# Set destination directories
if [ "$TARGET" = "user" ]; then
    DEST_AGENTS="$HOME/.claude/agents"
    DEST_COMMANDS="$HOME/.claude/commands"
else
    DEST_AGENTS="$PROJECT_PATH/.claude/agents"
    DEST_COMMANDS="$PROJECT_PATH/.claude/commands"
fi

# Create directories
mkdir -p "$DEST_AGENTS" "$DEST_COMMANDS"

# Copy agents
echo "Installing subagents to $DEST_AGENTS ..."
for f in "$AGENTS_SRC"/sextant-*.md; do
    name="$(basename "$f")"
    cp "$f" "$DEST_AGENTS/$name"
    echo "  + $name"
done

# Copy commands
echo "Installing slash commands to $DEST_COMMANDS ..."
for f in "$COMMANDS_SRC"/sextant-*.md; do
    name="$(basename "$f")"
    cp "$f" "$DEST_COMMANDS/$name"
    echo "  + $name"
done

echo ""
echo "Done. Sextant Claude Code adapter installed ($TARGET)."
echo ""
echo "Next steps:"
echo "  1. Append the CLAUDE.md snippet to your project:"
echo "     cat $SCRIPT_DIR/CLAUDE.md.snippet >> $PROJECT_PATH/CLAUDE.md"
echo ""
echo "  2. Run the bootstrap script to initialize knowledge files in your project:"
echo "     $SCRIPT_DIR/../../scripts/bootstrap.sh --target $PROJECT_PATH"
echo ""
echo "  3. (Optional) Enable session hooks:"
echo "     See $SCRIPT_DIR/hooks/README.md"
