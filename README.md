# Sextant

**An engineering mindset framework that tells you where you are when coding with AI.**

[中文文档](README.zh.md)

---

## What is Sextant?

A nautical sextant helps navigators determine their position at sea by measuring angles between celestial bodies and the horizon. It doesn't make the ship faster — it tells the captain exactly where the ship is at every critical decision point.

Sextant does the same for AI-assisted coding.

AI-generated code looks correct line by line. Tests pass. Everything seems fine. But you don't know if you've drifted — whether the abstraction is over-engineered, whether the implementation has diverged from the original spec, whether you're paying the cost of imagined future requirements.

**Sextant is not a tool to make AI smarter or make you code faster. It's a tool that tells you whether you're still on the right course at every critical decision point.**

## Why Sextant?

AI coding tools today have strong generation capability but lack engineering judgment. Four real problems:

1. **No project-wide view.** Each task is treated as an island. The model doesn't know how the current feature fits into the project, its relationship with existing parts, or whether it duplicates something elsewhere.

2. **Over-engineering by default.** Models slide toward "more complete engineering practice": more abstraction layers, more files, more interfaces, more future extension points. Each looks reasonable in isolation; collectively they're out of control.

3. **Self-writing, self-testing blind spots.** The same mental flow writes the spec, designs the solution, implements it, and then validates it. The result is self-consistency, not independent verification.

4. **Context amnesia.** A new session doesn't remember where the project evolved to, what the last few tasks did, why something was designed this way, or which failure paths have already been tried.

## How It Works

Sextant externalizes engineering discipline into a runtime protocol:

### 5 Roles

| Role         | Responsibility                                                                 |
| ------------ | ------------------------------------------------------------------------------ |
| **spec**     | Distill requirements into executable specs with clear boundaries               |
| **planner**  | Propose the minimal viable approach, favor boring defaults                     |
| **builder**  | Implement strictly within the plan's declared scope                            |
| **reviewer** | Reduction-Review: find deletable content, complexity smells, verification gaps |
| **rca**      | Root cause analysis — only appears after failures, rework, or incidents        |

> The reviewer's core contract: always output a `deletion_proposals` field. If nothing can be deleted, explicitly write `none`. The reviewer is an adversary, not an approver.

### 5 Phases

**Spec → Plan → Build → Verify → Record**

Verify is a phase, not a role. It's handled by deterministic tooling (tests, types, lint, hooks) combined with the reviewer examining the diff.

### 3 Task Levels

- **L0** — Minor text changes, small style fixes, low-risk small bugs
- **L1** — New page, one API endpoint, small-scope module changes
- **L2** — Data model changes, architecture migrations, auth/payment/sync modifications

Levels only escalate, never downgrade. Override with `--force-l0/l1/l2`.

### Knowledge System

Four knowledge objects, each with a defined invalidation condition:

| File                       | Invalidated when                         |
| -------------------------- | ---------------------------------------- |
| `SEXTANT.md`               | Current technical constraints change     |
| `modules/*/EVOLUTION.md`   | Module history path changes              |
| `PROJECT_EVOLUTION_LOG.md` | Project-level long-term decisions update |
| `hook-registry.json`       | The rule itself changes                  |

**Principle:** Only keep content that would change a current engineering judgment. Not an archive.

## Design Principles

1. **Concentrate verification density at the smallest artifact.** Every token spent validating a spec prevents dozens of tokens of wrong code downstream.
2. **Adversarial structure over model count.** True adversarial review comes from context isolation + responsibility isolation + output contract isolation — independent of model brand.
3. **Deterministic logic before LLM.** Dispatching, task classification, tool gating: deterministic first. LLM only where genuine judgment is needed.
4. **Verification independence from "looking at products, not reasoning."** The reviewer receives only upstream structured output, never the upstream reasoning process.
5. **Every layer must be retirable.** Sextant serves the capability gap of 2026. Each mechanism can be independently disabled as models improve.

## Quick Start with Claude Code

**Requirements:** Claude Code CLI or desktop app.

```sh
# 1. Clone Sextant
git clone https://github.com/SaoNian/Sextant

# 2. Initialize knowledge files in your project
cd Sextant
./scripts/bootstrap.sh --target /path/to/your-project

# 3. Install the Claude Code adapter
./adapters/claude-code/install.sh --project --path /path/to/your-project

# 4. Append Sextant instructions to your project's CLAUDE.md
cat adapters/claude-code/CLAUDE.md.snippet >> /path/to/your-project/CLAUDE.md
```

Then in Claude Code within your project:

```
/sextant-spec     # Start a task: define scope and acceptance criteria
/sextant-plan     # Choose the minimal implementation approach
/sextant-build    # Implement within the approved plan
/sextant-verify   # Run tools + adversarial review
/sextant-record   # Write back knowledge, close the task
```

## Status

**v0.0.1** — Core text layer and Claude Code adapter complete.

- `core/roles/` — 5 role prompts (reviewer, spec, planner, builder, rca)
- `core/templates/` — 5 output templates
- `core/rules/` — task classification, stage gates, rollback rules
- `core/knowledge/` — 4 knowledge file initialization templates
- `adapters/claude-code/` — subagents, slash commands, hooks, install script
- `scripts/bootstrap.sh` — knowledge layout initializer

Generic CLI and Trace system planned for v0.2. See [roadmap](docs/roadmap.md).

## License

MIT
