# Changelog

All notable changes to Sextant are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
