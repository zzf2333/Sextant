# Sextant Claude Code Adapter

This adapter integrates Sextant into [Claude Code](https://claude.ai/code) using four mechanisms:

| Mechanism | Location | Purpose |
|---|---|---|
| Subagents | `agents/sextant-*.md` | Role-specific AI contexts with session isolation |
| Slash commands | `commands/sextant-*.md` | Stage-by-stage workflow drivers |
| CLAUDE.md snippet | `CLAUDE.md.snippet` | Project-level protocol instructions |
| Hooks | `hooks/settings.example.json` | Deterministic session guardrails |

## Capability Boundary

This adapter's capabilities define the future `sextant` CLI's v0.2 feature set.
Each command file documents its CLI equivalent (e.g., `sextant spec`).
The adapter does not implement anything the CLI will not also implement.

## Installation

```sh
# Clone Sextant
git clone https://github.com/SaoNian/Sextant

# Install adapter (project-level)
cd Sextant
./adapters/claude-code/install.sh --project --path /path/to/your-project

# Or install for all projects (user-level)
./adapters/claude-code/install.sh --user
```

## Usage

After installation, in Claude Code within your project:

```
/sextant-spec     # Define scope and acceptance criteria
/sextant-plan     # Produce the minimal implementation approach
/sextant-build    # Implement within the approved plan
/sextant-verify   # Run tools + adversarial review
/sextant-record   # Write back knowledge, close the task
```

## Subagents

Each subagent maps to one Sextant role and provides session isolation:

| Subagent | Role | When to use |
|---|---|---|
| `sextant-reviewer` | reviewer | After spec, plan, and build stages |
| `sextant-spec` | spec | To define task scope and acceptance criteria |
| `sextant-planner` | planner | To choose the minimal implementation approach |
| `sextant-builder` | builder | To implement within approved spec and plan |
| `sextant-rca` | rca | After confirmed failures or rework events only |

## Hooks

See `hooks/README.md` for how to enable advisory session guardrails.
