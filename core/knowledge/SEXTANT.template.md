# SEXTANT.md — Project Truth File

> **Before adding anything here:** ask "Will this change a future engineering judgment?"
> If the answer is no, do not add it. This file is not a README or an architecture doc.
> It records only what is currently true and non-obvious about this project.

This file is read by Sextant roles at the start of every task. Keep it current and minimal.
Outdated entries are worse than no entries — remove or update them when they become stale.

---

## Current Tech Stack

> List the primary technologies in active use. Remove anything that has been replaced.

- Language: <!-- e.g. TypeScript 5.x -->
- Runtime: <!-- e.g. Node.js 20 -->
- Framework: <!-- e.g. Next.js 14 -->
- Data store: <!-- e.g. PostgreSQL 16 via Prisma -->
- Test runner: <!-- e.g. Vitest -->
- Lint / format: <!-- e.g. ESLint + Prettier -->

---

## Default Preferences

> Decisions already made — do not re-litigate these in specs or plans unless SEXTANT.md is updated.

- <!-- e.g. "Prefer server components over client components unless interactivity is required" -->
- <!-- e.g. "All new API routes use tRPC; REST routes are legacy and not to be extended" -->

---

## Explicit Non-Goals

> Things this project deliberately does not do. Proposals that contradict these require explicit
> SEXTANT.md amendment first — not just a plan note.

- <!-- e.g. "No mobile-native app; web only" -->
- <!-- e.g. "No multi-tenancy in v1; all data is single-tenant" -->

---

## Known Constraints

> Hard limits the environment imposes that cannot be changed by a task.

- <!-- e.g. "Deployment target is a single VPS with 2GB RAM — no Kubernetes" -->
- <!-- e.g. "External API X has a rate limit of 100 req/min; all callers must respect this" -->

---

## Verification Commands

> Commands run by /sextant-verify (and /sextant) during the Verify stage.
> If this section is absent or empty, the adapter will auto-detect from project structure.
> Set explicitly to pin specific commands or add custom checks.

verify_commands:
  # - npm test
  # - npx tsc --noEmit
  # - npm run lint
