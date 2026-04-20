# Changelog

All notable changes to Sextant are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.0.7] - 2026-04-20

### Changed

- Knowledge files (`SEXTANT.md`, `PROJECT_EVOLUTION_LOG.md`, `hook-registry.json`) moved
  from project root to `.sextant/` subdirectory. `bootstrap.sh` and `sextant-init` now
  write to `.sextant/`; `install.sh` checks `.sextant/$kf`. All command, agent, role,
  template, and doc references updated. **Breaking change for existing projects** — move
  files manually: `mv SEXTANT.md PROJECT_EVOLUTION_LOG.md hook-registry.json .sextant/`.

## [0.0.6] - 2026-04-20

### Added

- `/sextant-init` — new command for onboarding existing projects. Scans project
  manifests (`package.json`, `pyproject.toml`, `go.mod`, `Cargo.toml`, etc.) to
  auto-detect tech stack, frameworks, test runners, and module layout, then generates
  the four Sextant knowledge files with pre-filled content. Solves the cold-start
  problem where bootstrapping an existing project produced empty templates with no
  useful context for the AI. Supports `--force` for silent re-initialization.

## [0.0.5] - 2026-04-20

### Changed

- All repository URLs updated from `SaoNian/Sextant` to `zzf2333/Sextant`.
  Affected files: `README.md`, `README.zh.md`, `adapters/claude-code/CLAUDE.md.snippet`,
  `adapters/claude-code/README.md`, `docs/quickstart.md`.

## [0.0.4] - 2026-04-20

### Changed

- `install.sh` — bootstrap and CLAUDE.md snippet injection are now **on by default**.
  Running `./install.sh --project --path /your/project` installs agents, commands,
  initializes knowledge files, and appends the CLAUDE.md snippet in one shot.
  Use `--skip-bootstrap` or `--skip-snippet` to opt out of specific steps.
  Old `--bootstrap` and `--with-snippet` flags are preserved as silent no-ops for
  backward compatibility.
- `install.sh` — readiness summary now says "Setup incomplete — re-run with defaults"
  (instead of "[Required] steps remaining") when opt-out flags left setup incomplete.
  "Project is ready." message is unchanged.
- `install.sh` — `usage()` updated to document `--skip-bootstrap` and `--skip-snippet`
  as the opt-out flags; old flags removed from help text (still accepted silently).
- `adapters/claude-code/README.md` — one-shot install example simplified to remove
  now-default flags. Added note about `--skip-snippet` / `--skip-bootstrap` for
  agents/commands-only installs.
- `docs/quickstart.md` — install example updated to match new one-command default.
- `README.md` / `README.zh.md` — version badge updated; install example simplified.
- `SEXTANT.md` — filled in with Sextant's actual tech stack (Python 3.11+, stdlib only,
  pytest, POSIX sh). Was previously the blank template skeleton.
- `adapters/claude-code/commands/sextant.md` — reduced happy-path friction:
  - Active trace with matching description now **auto-resumes** (was: "Resume or start new?" prompt)
  - No-arg invocation now **auto-continues the most recent active trace** (was: list top 3 and ask)
  - L0 and L1 tasks now proceed immediately after classification (was: "full flow or go to Build?" prompt)
  - Plan-approved pause simplified to one line: "Run `/sextant` to build." (was: 5-line option box)
  - Build-complete pause simplified to one line: "Run `/sextant` to verify and close."
  - Record fast-close with no signals now closes silently (was: "Confirm? [y/n]" prompt)
  - Meaningful pause points unchanged: L2 escalation, reviewer rejection, verify failure,
    scope creep, durable knowledge delta

### Fixed

- `cli/status.py` — Gate 1 and Gate 2 pending messages referenced `/sextant-review`
  (a command that has never existed). Corrected to `re-run /sextant-spec` and
  `re-run /sextant-plan` respectively. This was an incomplete fix from v0.0.3.

### Design note

v0.0.4 is a default-path polish release. No phases, roles, gates, or review behavior
changed. The goal is to make Sextant feel coherent and trustworthy on first contact.

## [0.0.3] - 2026-04-19

### Added

- `/sextant` — new primary entry command. Accepts a task description or resumes the
  most recent active trace. Runs Spec + Spec Review + Plan + Plan Review automatically,
  pauses at implementation decision point, then Build on next invocation, then Verify +
  Record on the third. Pauses only at meaningful human decision points.
- `/sextant-status` — new state visibility command. Reports current task ID, level,
  stage, last gate, blockers, and recommended next action. Supports `--all` flag to
  list all traces.
- `docs/quickstart.md` — 5-minute quickstart guide from install to first completed task.
- `install.sh --bootstrap` flag — chains install → `bootstrap.sh` in a single command.
- `install.sh --with-snippet` flag — appends `CLAUDE.md.snippet` automatically.
- `install.sh --check` mode — readiness self-check without installing anything.
- `install.sh --force` flag — allows overwriting existing installed files.
- `core/knowledge/SEXTANT.template.md`: added `verify_commands` section so users know
  where to pin verification commands.
- `hooks/settings.example.json`: three enforcement levels (advisory / team / strict)
  with named example blocks; choose the level and copy its hooks array.
- `hooks/README.md`: enforcement level table, setup instructions, and guidance on when
  to use each level.

### Changed

- `/sextant-spec` now auto-invokes the spec reviewer at the end of its flow (consistent
  with how `/sextant-plan` auto-reviews the plan). Gate 1 check in `/sextant-plan` now
  always finds `review-spec.md` when `/sextant-spec` was used correctly. The broken
  reference to a nonexistent `/sextant-review` command is removed.
- `/sextant-spec` Step 7 next-step prompt updated: "Spec approved. Run `/sextant-plan`
  to continue." (was: "Run `/sextant-review --stage spec`" — that command never existed.)
- `/sextant-plan` gate failure message now includes the specific reason (missing file vs.
  rejected verdict) and a clear recovery path.
- `/sextant-verify` auto-detects verification commands from `package.json`, `pyproject.toml`,
  `go.mod`, and `Cargo.toml` when `verify_commands` is not set in `SEXTANT.md`.
  No longer asks the user for commands if they can be inferred from project structure.
- `/sextant-record` pre-analyzes the build diff for durable knowledge signals before
  presenting the P5 checklist. If no signals are detected, offers a fast-close path
  (confirm close without writebacks). Full P5 flow still available via `--full` flag.
- `install.sh` is now idempotent: skips already-installed files without overwriting,
  detects whether the CLAUDE.md snippet is already present, and prints a final readiness
  summary that clearly distinguishes "done" from "still needed".
- Stop hook is now conditional: only prints the verify reminder when at least one trace
  has a `build-summary.md` but no `review-build.md` (was: unconditional, producing noise
  on every session end regardless of task state).
- `CLAUDE.md.snippet` updated: `/sextant` is now the recommended primary command;
  explicit stage commands listed as "for advanced control"; `/sextant-status` added.
- `adapters/claude-code/README.md` updated: one-shot install example, command reference
  table with explicit vs. `/sextant` guidance, hooks enforcement levels summary.

### Design note

v0.0.3 is a usability release, not a philosophy rewrite. Every gate, reviewer session,
and verification step still runs. The `/sextant` command orchestrates non-decision steps
automatically; it does not skip them. Record's fast-close path skips ceremony only when
signal analysis confirms there is nothing to write — not by default. Hooks default to
advisory; enforcement is opt-in.

## [0.0.2] - 2026-04-15

### Added

- `sextant status <task_id>` — read-only task trace snapshot: current stage,
  artifact versions, pending gate, rollback and bypass markers
- `sextant lint <task_id>` — minimum-trust structure validation of trace
  artifacts; integrated as Gate 4 pre-condition in `/sextant-verify`
- `sextant metrics` — reviewer health metric aggregation: non-empty
  deletion_proposals ratio, rejection ratio, consecutive-none-tasks ratio
- `core/snippets/check-upstream-gate.md` — shared gate check fragment;
  adapter commands now reference it instead of duplicating gate logic
- Python CLI package (`cli/`, `pyproject.toml`) — stdlib-only, Python 3.11+
- 81 new CLI tests (parsers, status, lint, metrics); total test count 206
- Sextant logo and architecture diagrams added to README

### Changed

- `sextant-plan`, `sextant-build`, `sextant-record` gate checks consolidated
  to a single shared snippet reference — eliminates DRY violation
- `sextant-build` and `sextant-record` now accept `approved-with-conditions`
  (aligned with `sextant-plan`); fixes undocumented semantic divergence
- `core/templates/spec.md`: added `forced_level` and `override_reason` fields
- `core/templates/review.md`: added `review_version` field
- `core/templates/record.md`: added `record_version` field
- `core/rules/rollback.md`: explicit `*_version` bump rules with versioned
  artifact type list and bump criteria
- `docs/design.md`: flow guarantee architecture and CLI tool layer documented

## [0.0.1] - 2026-04-15

### Added

- Core text layer: 5 role prompts (reviewer, spec, planner, builder, rca)
- 5 structured output templates (review, spec, plan, rca, record)
- 3 rule files (task-classification, stage-gates, rollback)
- 4 knowledge file initialization templates (SEXTANT, EVOLUTION, PROJECT_EVOLUTION_LOG, hook-registry)
- Claude Code adapter: 5 subagents, 5 slash commands, hooks example, CLAUDE.md snippet, install script
- `scripts/bootstrap.sh` — initializes knowledge layout in an existing project
- Deterministic test suite: 199 tests across 4 suites (structure, bootstrap, install, JSON)
- CI/CD: GitHub Actions workflows for test gating and automated GitHub Releases
- Maintainer release tooling: `scripts/release.sh`, `scripts/bump-version.sh`
