# Sextant Hooks for Claude Code

These hooks add lightweight guardrails to the Claude Code session lifecycle.
They use Claude Code's `hooks` mechanism in `settings.json`.

## What the Hooks Do

### Stop hook

Reminds you to run `/sextant-verify` and `/sextant-record` before ending a session
if you completed a Build stage. This prevents tasks from being abandoned mid-flow.

### PreToolUse hook (git commit)

Before any `git commit` command runs, checks if the current task has a build review.
If not, it prints a warning. It does **not** block the commit — it is advisory only.

## How to Enable

1. Open your Claude Code settings:
   - **User-level** (all projects): `~/.claude/settings.json`
   - **Project-level** (one project): `<project>/.claude/settings.json`

2. Merge the `hooks` array from `settings.example.json` into your settings file.

3. The hooks take effect immediately — no restart needed.

## When to Enable

Enable these hooks in **your business/product projects** that use Sextant, not in the
Sextant repo itself (the Sextant repo uses these files only as templates and examples).

## Customizing

- To make the commit hook blocking (instead of advisory), change the command to exit with
  a non-zero code: add `; exit 1` after the warning echo.
- To add project-specific hooks, add entries to `hook-registry.json` in your project root
  and write a corresponding shell command in a PreToolUse hook entry.
