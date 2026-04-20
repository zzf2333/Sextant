#!/usr/bin/env sh
# Sextant Claude Code adapter installer
# Installs sextant-* subagents and slash commands into a Claude Code context.
#
# Usage:
#   ./install.sh --user              # install to ~/.claude/ (all projects)
#   ./install.sh --project           # install to ./.claude/ (current project)
#   ./install.sh --project --path /path/to/project
#
# By default, the installer also initializes knowledge files and injects the
# CLAUDE.md snippet. Use opt-out flags to disable parts of this:
#   --skip-bootstrap   skip knowledge file initialization
#   --skip-snippet     skip CLAUDE.md snippet injection
#   --force            overwrite existing installed files
#   --check            run readiness check only, no install

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
AGENTS_SRC="$SCRIPT_DIR/agents"
COMMANDS_SRC="$SCRIPT_DIR/commands"
SNIPPET_SRC="$SCRIPT_DIR/CLAUDE.md.snippet"
BOOTSTRAP_SCRIPT="$SCRIPT_DIR/../../scripts/bootstrap.sh"

# ── colour helpers ────────────────────────────────────────────────────────────
_green()  { printf '\033[0;32m%s\033[0m\n' "$*"; }
_yellow() { printf '\033[0;33m%s\033[0m\n' "$*"; }
_red()    { printf '\033[0;31m%s\033[0m\n' "$*"; }
_dim()    { printf '\033[2m%s\033[0m\n'    "$*"; }

_ok()   { printf '  \033[0;32m✓\033[0m  %s\n' "$*"; }
_skip() { printf '  \033[2m–\033[0m  %s\n'    "$*"; }
_warn() { printf '  \033[0;33m!\033[0m  %s\n' "$*"; }
_fail() { printf '  \033[0;31m✗\033[0m  %s\n' "$*"; }

usage() {
    cat <<EOF
Usage: $0 --user | --project [--path <project_path>] [options]

  --user              Install to ~/.claude/ (applies to all projects)
  --project           Install to ./.claude/ (current project only)
  --path <path>       Use <path> as project root (with --project)

Options:
  --skip-bootstrap    Skip knowledge file initialization (SEXTANT.md, etc.)
  --skip-snippet      Skip CLAUDE.md snippet injection
  --force             Overwrite existing installed files
  --check             Run readiness check only — do not install anything

EOF
    exit 1
}

# ── argument parsing ──────────────────────────────────────────────────────────
TARGET=""
PROJECT_PATH="$(pwd)"
OPT_BOOTSTRAP=1
OPT_SNIPPET=1
OPT_FORCE=0
OPT_CHECK=0

while [ "$#" -gt 0 ]; do
    case "$1" in
        --user)             TARGET="user";        shift ;;
        --project)          TARGET="project";     shift ;;
        --path)             PROJECT_PATH="$2";    shift 2 ;;
        --bootstrap)        OPT_BOOTSTRAP=1;      shift ;;  # no-op: now default
        --with-snippet)     OPT_SNIPPET=1;        shift ;;  # no-op: now default
        --skip-bootstrap)   OPT_BOOTSTRAP=0;      shift ;;
        --skip-snippet)     OPT_SNIPPET=0;        shift ;;
        --force)            OPT_FORCE=1;          shift ;;
        --check)            OPT_CHECK=1;          shift ;;
        *)                  usage ;;
    esac
done

# --check requires no TARGET
if [ "$OPT_CHECK" -eq 1 ] && [ -z "$TARGET" ]; then
    # default to project check
    TARGET="project"
fi

[ -z "$TARGET" ] && usage

# ── destination directories ───────────────────────────────────────────────────
if [ "$TARGET" = "user" ]; then
    DEST_AGENTS="$HOME/.claude/agents"
    DEST_COMMANDS="$HOME/.claude/commands"
    DEST_CLAUDE_MD="$HOME/CLAUDE.md"
else
    DEST_AGENTS="$PROJECT_PATH/.claude/agents"
    DEST_COMMANDS="$PROJECT_PATH/.claude/commands"
    DEST_CLAUDE_MD="$PROJECT_PATH/CLAUDE.md"
fi

# ── readiness check ───────────────────────────────────────────────────────────
run_check() {
    echo ""
    _green "Sextant readiness check"
    echo ""

    # agents
    AGENTS_OK=1
    for f in "$AGENTS_SRC"/sextant-*.md; do
        name="$(basename "$f")"
        if [ -f "$DEST_AGENTS/$name" ]; then
            _ok "Agent: $name"
        else
            _fail "Agent missing: $name"
            AGENTS_OK=0
        fi
    done

    # commands
    CMDS_OK=1
    for f in "$COMMANDS_SRC"/sextant*.md; do
        name="$(basename "$f")"
        if [ -f "$DEST_COMMANDS/$name" ]; then
            _ok "Command: $name"
        else
            _fail "Command missing: $name"
            CMDS_OK=0
        fi
    done

    # CLAUDE.md snippet
    SNIPPET_OK=0
    if [ -f "$DEST_CLAUDE_MD" ] && grep -q "Sextant Engineering Protocol" "$DEST_CLAUDE_MD" 2>/dev/null; then
        _ok "CLAUDE.md: Sextant snippet present"
        SNIPPET_OK=1
    else
        _warn "CLAUDE.md: Sextant snippet not found (run with --with-snippet)"
    fi

    # knowledge files
    KNOWLEDGE_OK=1
    for kf in SEXTANT.md PROJECT_EVOLUTION_LOG.md hook-registry.json; do
        if [ -f "$PROJECT_PATH/$kf" ]; then
            _ok "Knowledge file: $kf"
        else
            _warn "Knowledge file missing: $kf (run with --bootstrap)"
            KNOWLEDGE_OK=0
        fi
    done

    echo ""
    if [ "$AGENTS_OK" -eq 1 ] && [ "$CMDS_OK" -eq 1 ] && [ "$SNIPPET_OK" -eq 1 ] && [ "$KNOWLEDGE_OK" -eq 1 ]; then
        _green "Project is ready. Start with: /sextant \"what you want to build\""
    else
        _yellow "Project is not fully ready. See warnings above."
        if [ "$AGENTS_OK" -eq 0 ] || [ "$CMDS_OK" -eq 0 ]; then
            echo ""
            echo "  Run: $SCRIPT_DIR/install.sh --project --path $PROJECT_PATH --bootstrap --with-snippet"
        fi
    fi
    echo ""
}

if [ "$OPT_CHECK" -eq 1 ]; then
    run_check
    exit 0
fi

# ── install ───────────────────────────────────────────────────────────────────
echo ""
_green "Installing Sextant Claude Code adapter ($TARGET)"
echo ""

# Create destination directories
mkdir -p "$DEST_AGENTS" "$DEST_COMMANDS"

# Install agents
echo "Agents → $DEST_AGENTS"
for f in "$AGENTS_SRC"/sextant-*.md; do
    name="$(basename "$f")"
    dest="$DEST_AGENTS/$name"
    if [ -f "$dest" ] && [ "$OPT_FORCE" -eq 0 ]; then
        _skip "$name (already installed, use --force to overwrite)"
    else
        cp "$f" "$dest"
        _ok "$name"
    fi
done

echo ""

# Install commands
echo "Commands → $DEST_COMMANDS"
for f in "$COMMANDS_SRC"/sextant*.md; do
    name="$(basename "$f")"
    dest="$DEST_COMMANDS/$name"
    if [ -f "$dest" ] && [ "$OPT_FORCE" -eq 0 ]; then
        _skip "$name (already installed, use --force to overwrite)"
    else
        cp "$f" "$dest"
        _ok "$name"
    fi
done

echo ""

# ── optional: bootstrap ───────────────────────────────────────────────────────
if [ "$OPT_BOOTSTRAP" -eq 1 ]; then
    echo "Bootstrapping knowledge files → $PROJECT_PATH"
    if [ ! -f "$BOOTSTRAP_SCRIPT" ]; then
        _warn "bootstrap.sh not found at $BOOTSTRAP_SCRIPT — skipping"
    else
        if sh "$BOOTSTRAP_SCRIPT" --target "$PROJECT_PATH" 2>&1 | while IFS= read -r line; do
            _dim "  $line"
        done; then
            _ok "Knowledge files initialized"
        else
            _warn "Bootstrap completed with warnings — check output above"
        fi
    fi
    echo ""
fi

# ── optional: CLAUDE.md snippet ───────────────────────────────────────────────
if [ "$OPT_SNIPPET" -eq 1 ]; then
    if grep -q "Sextant Engineering Protocol" "$DEST_CLAUDE_MD" 2>/dev/null; then
        _skip "CLAUDE.md: Sextant snippet already present"
    else
        if [ -f "$DEST_CLAUDE_MD" ]; then
            printf '\n' >> "$DEST_CLAUDE_MD"
            cat "$SNIPPET_SRC" >> "$DEST_CLAUDE_MD"
            _ok "CLAUDE.md: snippet appended to $DEST_CLAUDE_MD"
        else
            cp "$SNIPPET_SRC" "$DEST_CLAUDE_MD"
            _ok "CLAUDE.md: created at $DEST_CLAUDE_MD"
        fi
    fi
    echo ""
fi

# ── readiness summary ─────────────────────────────────────────────────────────
echo ""
_green "Installation complete"
echo ""

NEED_SNIPPET=0
NEED_BOOTSTRAP=0

if ! grep -q "Sextant Engineering Protocol" "$DEST_CLAUDE_MD" 2>/dev/null; then
    NEED_SNIPPET=1
fi

for kf in SEXTANT.md PROJECT_EVOLUTION_LOG.md hook-registry.json; do
    if [ ! -f "$PROJECT_PATH/$kf" ]; then
        NEED_BOOTSTRAP=1
        break
    fi
done

if [ "$NEED_SNIPPET" -eq 1 ] || [ "$NEED_BOOTSTRAP" -eq 1 ]; then
    _yellow "Setup incomplete — run with defaults to finish:"
    echo ""
    echo "  $SCRIPT_DIR/install.sh --project --path $PROJECT_PATH --force"
    echo ""
    if [ "$NEED_SNIPPET" -eq 1 ]; then
        _warn "CLAUDE.md snippet not injected (re-run without --skip-snippet)"
    fi
    if [ "$NEED_BOOTSTRAP" -eq 1 ]; then
        _warn "Knowledge files not initialized (re-run without --skip-bootstrap)"
    fi
else
    _green "Project is ready."
fi

echo ""
echo "  [Optional] Enable session hooks — see adapters/claude-code/hooks/README.md"
echo ""
echo "  Start with:"
echo "    /sextant \"what you want to build\""
echo ""
echo "  Check readiness at any time:"
echo "    $SCRIPT_DIR/install.sh --check"
echo ""
