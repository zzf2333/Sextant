# Sextant Claude Code Adapter

This adapter integrates Sextant into [Claude Code](https://claude.ai/code) using four mechanisms:

| Mechanism | Location | Purpose |
|---|---|---|
| Subagents | `agents/sextant-*.md` | Role-specific AI contexts with session isolation |
| Slash commands | `commands/sextant*.md` | Stage-by-stage workflow drivers |
| CLAUDE.md snippet | `CLAUDE.md.snippet` | Project-level protocol instructions |
| Hooks | `hooks/settings.example.json` | Deterministic session guardrails |

## Capability Boundary

This adapter's capabilities define the future `sextant` CLI's v0.2 feature set.
Each command file documents its CLI equivalent (e.g., `sextant spec`).
The adapter does not implement anything the CLI will not also implement.

---

## Installation

### One-shot install (recommended)

```sh
git clone https://github.com/zzf2333/Sextant
cd Sextant
./adapters/claude-code/install.sh --project --path /path/to/your-project
```

This single command:
1. Installs all agents and slash commands
2. Initializes project knowledge files (`.sextant/SEXTANT.md`, `.sextant/PROJECT_EVOLUTION_LOG.md`, `.sextant/hook-registry.json`)
3. Appends the Sextant protocol snippet to `CLAUDE.md`

After install, your project is ready to use. If you need to update the CLAUDE.md snippet later, re-run with `--force`.

### User-level install (applies to all projects)

```sh
./adapters/claude-code/install.sh --user
```

### Install without snippet or bootstrap (agents and commands only)

```sh
./adapters/claude-code/install.sh --project --path /your/project \
  --skip-snippet --skip-bootstrap
```

### Manual install (step by step)

```sh
# 1. Install agents and commands only
./adapters/claude-code/install.sh --project --path /your/project --skip-snippet --skip-bootstrap

# 2. Append CLAUDE.md snippet manually
cat adapters/claude-code/CLAUDE.md.snippet >> /your/project/CLAUDE.md

# 3. Initialize knowledge files manually
scripts/bootstrap.sh --target /your/project

# 4. (Optional) Enable session hooks — see hooks/README.md
```

### Reinstalling or upgrading

```sh
./adapters/claude-code/install.sh --project --path /your/project --force
```

The `--force` flag overwrites existing agent and command files. It does not touch
`CLAUDE.md` or knowledge files.

### Check readiness

```sh
./adapters/claude-code/install.sh --check
```

Prints which components are installed, what is missing, and whether the project is
ready to use.

---

## First task

Once installed, open Claude Code in your project and run:

```
/sextant "describe what you want to build"
```

That's it. The command handles spec, review, plan, and pauses at the first decision
point (plan approval). For small tasks it may complete in two or three invocations.

---

## Command reference

### Primary command

| Command | Purpose |
|---|---|
| `/sextant <task>` | Start or resume a task. The recommended default. |

### Explicit stage commands

| Command | Stage | Use when |
|---|---|---|
| `/sextant-spec` | Spec | You want explicit control over spec writing + review |
| `/sextant-plan` | Plan | You want explicit control over plan selection |
| `/sextant-build` | Build | You want explicit control over implementation |
| `/sextant-verify` | Verify | You want explicit control over verification |
| `/sextant-record` | Record | You want explicit control over knowledge writebacks |

### Utility commands

| Command | Purpose |
|---|---|
| `/sextant-status` | Show task state, current stage, blockers, and next action |

### When to use explicit vs. `/sextant`

- **L0/L1 tasks, standard work** → `/sextant` handles everything
- **L2 tasks** (data model, auth, payment, sync) → prefer explicit stage commands for
  step-by-step review at each gate
- **Debugging or picking up mid-flow** → use explicit commands + `/sextant-status`

---

## Subagents

Each subagent maps to one Sextant role and provides session isolation:

| Subagent | Role | Invoked by |
|---|---|---|
| `sextant-spec` | spec | `/sextant`, `/sextant-spec` |
| `sextant-planner` | planner | `/sextant`, `/sextant-plan` |
| `sextant-builder` | builder | `/sextant`, `/sextant-build` |
| `sextant-reviewer` | reviewer | `/sextant`, `/sextant-plan`, `/sextant-verify` |
| `sextant-rca` | rca | Manual — after confirmed failures only |

The reviewer runs automatically after spec, after plan, and after build. It is always
a fresh session with no carry-over from prior review stages — this is intentional.

---

## Hooks

Session hooks add guardrails at the session boundary. Three enforcement levels are
available:

| Level | Behavior |
|---|---|
| `advisory` | Warnings only. Default. |
| `team` | Blocks `git commit` when build review is missing. |
| `strict` | Blocks commit if review is missing OR scope_creep_flags are unresolved. |

See `hooks/README.md` for setup instructions and `hooks/settings.example.json` for
the full hook configurations.
