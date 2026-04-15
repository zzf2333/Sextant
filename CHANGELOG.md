# Changelog

All notable changes to Sextant are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
