[中文文档](README.zh.md)

<div align="center">

<img src="logo.svg" width="120" height="120" alt="Sextant Logo"/>

<h1>Sextant</h1>

<p><strong>An engineering mindset framework that tells you where you are when coding with AI.</strong></p>

<p>
  <a href="https://github.com/SaoNian/Sextant/stargazers"><img src="https://img.shields.io/github/stars/SaoNian/Sextant?style=flat-square&color=a855f7" alt="GitHub Stars"/></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-10b981?style=flat-square" alt="License MIT"/></a>
  <img src="https://img.shields.io/badge/version-0.0.1-3b82f6?style=flat-square" alt="v0.0.1"/>
  <img src="https://img.shields.io/badge/Claude%20Code-adapter%20ready-f97316?style=flat-square" alt="Claude Code"/>
</p>

</div>

---

A nautical sextant doesn't make the ship faster — it tells the captain exactly where the ship is at every critical decision point. Without it, you're navigating by feel.

Sextant does the same for AI-assisted coding.

AI-generated code looks correct line by line. Tests pass. Everything seems fine. But you don't know if you've drifted — whether the abstraction is over-engineered, whether the implementation has diverged from the spec, whether you're paying the cost of imagined future requirements.

**Sextant is not a tool to make AI smarter or make you code faster. It's a tool that tells you whether you're still on course at every critical decision point.**

---

## The Problem

You're building a feature with Claude Code. You write the spec in your head, ask the AI to implement it, the tests pass, and it looks clean. Three days later:

- A second AI session re-introduces an abstraction you already rejected
- The implementation has three more files than the plan called for
- The reviewer (you, running on empty) approved a diff that solved the wrong problem

This isn't a model capability problem. Claude, GPT, Gemini — they're all capable. They just lack **engineering judgment** baked into the workflow.

Four real failure modes:

| Failure                                    | What Happens                                                                                                                                       |
| ------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| **No project-wide view**                   | Each session treats tasks as islands. Naming drift, duplicate logic, architectural contradictions accumulate silently.                             |
| **Over-engineering by default**            | Models slide toward "more complete" practice: extra abstraction layers, more files, more extension points. Each looks reasonable in isolation.     |
| **Self-writing, self-testing blind spots** | The same mental flow writes the spec, designs the solution, implements, then validates it. You get self-consistency, not independent verification. |
| **Context amnesia**                        | A new session doesn't know where the project evolved to, what the last task did, why something was designed this way.                              |

![Sextant Architecture](docs/diagrams/01-architecture.png)

---

## How It Works

Sextant externalizes engineering discipline into a runtime protocol: five context-isolated roles, five phases, and a knowledge system that only keeps what would change a current engineering judgment.

### 5 Roles

![Role Interactions](docs/diagrams/03-roles.png)

| Role         | Responsibility                                                                                  | Key Contract                                                                                                                         |
| ------------ | ----------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| **spec**     | Distills fuzzy requirements into an executable spec with explicit scope and acceptance criteria | Produces: scope, constraints, ambiguities, acceptance criteria, open decisions                                                       |
| **planner**  | Proposes the minimal viable approach, prefers boring defaults, avoids over-building             | Generates 1–2 candidates, selects the most economical path, declares full footprint                                                  |
| **builder**  | Implements strictly within the plan's declared scope                                            | Flags scope creep rather than committing it; runs hook-registry checks before declaring done                                         |
| **reviewer** | **Reduction-Review** — adversary, not approver                                                  | `deletion_proposals` is a required field. If nothing can be deleted, explicitly write `none`. Reviewer sees products, not reasoning. |
| **rca**      | Root cause analysis                                                                             | Only appears after confirmed failures, rework events, or incidents — never speculatively                                             |

> The reviewer runs in **three independent sessions**: after spec, after plan, after build. Each is a fresh adversarial context that only receives the upstream structured artifact — never the reasoning process that produced it.

### 5 Phases

![Workflow](docs/diagrams/02-workflow.png)

**Spec → Plan → Build → Verify → Record**

Verify is a phase, not a role. It's owned by the deterministic toolchain (tests, types, lint, hooks) plus the reviewer examining the diff. Not by the same agent that wrote the code.

### 3 Task Levels

Tasks are classified at the start. Levels only escalate, never downgrade:

| Level                   | Triggers                                                       | Required Flow                       |
| ----------------------- | -------------------------------------------------------------- | ----------------------------------- |
| **L0** — micro-task     | Text changes, style fixes, low-risk tiny bugs                  | Local verify + record               |
| **L1** — standard task  | New page, one API endpoint, small-scope module change          | Full 5-phase flow                   |
| **L2** — high-risk task | Data model changes, auth/payment/sync, architecture migrations | Strict reviewer + rollback thinking |

Override with `--force-l0`, `--force-l1`, or `--force-l2`.

### Knowledge System

Four knowledge files live in your project, versioned alongside your code. Each has a defined invalidation condition so the system stays lean — it's not an archive:

| File                       | Invalidated When                         | Content                                               |
| -------------------------- | ---------------------------------------- | ----------------------------------------------------- |
| `SEXTANT.md`               | Technical constraints change             | Current stack, explicit no-go rules, defaults         |
| `modules/*/EVOLUTION.md`   | Module history path changes              | Design decisions, rejected paths, accepted trade-offs |
| `PROJECT_EVOLUTION_LOG.md` | Project-level long-term decisions update | Cross-module choices, architecture trade-offs         |
| `hook-registry.json`       | The rule itself changes                  | Machine-checkable guardrails, deterministic gates     |

**Principle:** Only keep content that would change a current engineering judgment. Not an archive.

---

## Design Principles

1. **Concentrate verification density at the smallest artifact.** Every token spent validating a spec prevents dozens of tokens of wrong code downstream. Validate specs, not implementations.

2. **Adversarial structure over model count.** True adversarial review comes from context isolation + responsibility isolation + output contract isolation. Independent of model brand.

3. **Deterministic logic before LLM.** Task classification, tool gating, state transitions: deterministic first. LLM only where genuine judgment is needed.

4. **Verification independence from "looking at products, not reasoning."** The reviewer receives only upstream structured output — never the reasoning process or intermediate drafts.

5. **Every layer must be retirable.** Sextant serves the capability gap of 2026. Each mechanism can be independently disabled as models improve. This is health, not failure.

---

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
/sextant-spec     # Define scope and acceptance criteria
/sextant-plan     # Choose the minimal implementation approach
/sextant-build    # Implement within the approved plan
/sextant-verify   # Run tools + adversarial review
/sextant-record   # Write back knowledge, close the task
```

---

## Status

**v0.0.1** — Core text layer and Claude Code adapter complete.

| Component               | Status                                                 |
| ----------------------- | ------------------------------------------------------ |
| `core/roles/`           | 5 role prompts (reviewer, spec, planner, builder, rca) |
| `core/templates/`       | 5 output templates                                     |
| `core/rules/`           | Task classification, stage gates, rollback rules       |
| `core/knowledge/`       | 4 knowledge file initialization templates              |
| `adapters/claude-code/` | Subagents, slash commands, hooks, install script       |
| `scripts/bootstrap.sh`  | Knowledge layout initializer                           |

Generic CLI and Trace system planned for v0.2.

---

## License

MIT
