# Sextant Hooks for Claude Code

These hooks add session guardrails to Claude Code using the `hooks` mechanism in `settings.json`.
They enforce Sextant's verification discipline at the session boundary — catching common
mistakes before they become hard to undo.

## Enforcement Levels

Sextant provides three hook levels. Choose the one that fits your team's working style.

| Level | Stop hook | Commit gate | Best for |
|---|---|---|---|
| **advisory** | Warns about incomplete builds when session ends | Warning only — commit allowed | Solo work, exploration, initial adoption |
| **team** | Same warning | Blocks commit if build review is missing | Teams where discipline matters but trust is high |
| **strict** | Same warning | Blocks commit if review is missing OR scope_creep_flags unresolved | High-risk projects, L2-heavy work, regulated environments |

**Default**: advisory. No level blocks anything by default.

## What each hook does

### Stop hook (all levels)

Fires when a Claude Code session ends. Checks if any active task trace has a
`build-summary.md` without a `review-build.md` (i.e. build done but not verified).

- If found: prints a reminder with the task name.
- If nothing incomplete: silent.

### PreToolUse hook — git commit (all levels)

Fires before any `git commit` Bash command. Checks the most recent active task trace.

- **advisory**: warns if build review is missing, does not block.
- **team**: blocks (`exit 2`) if build review is missing. Warns if review is malformed.
- **strict**: blocks if review is missing OR if `scope_creep_flags` are unresolved in
  `build-summary.md`.

## How to enable

1. Open your Claude Code settings:
   - **User-level** (all projects): `~/.claude/settings.json`
   - **Project-level** (one project): `<project>/.claude/settings.json`

2. Pick a level from `settings.example.json` and copy its hooks array entries into
   your settings file under a top-level `"hooks"` key.

   Example — enabling the **team** level:
   ```json
   {
     "hooks": [
       { "event": "Stop", "hooks": [ ... ] },
       { "event": "PreToolUse", "hooks": [ ... ] }
     ]
   }
   ```
   Copy the entries from `hooks_team` in `settings.example.json`.

3. Hooks take effect immediately — no restart needed.

## When to enable these

Enable in your **product/business projects** that use Sextant, not in the Sextant
repo itself (these files are templates here, not active hooks).

- Solo project, learning Sextant → **advisory**
- Team repo with active L1 work → **team**
- L2 tasks (migrations, auth, payments), regulated code → **strict**

## Customizing

The hooks in `settings.example.json` are starting points. You can extend them to
check project-specific conditions — add your own entries to the `hooks` array or
write corresponding shell commands that read `.sextant/hook-registry.json` in your project root.

See `core/knowledge/hook-registry.template.json` for the format of project-level
deterministic rules.
