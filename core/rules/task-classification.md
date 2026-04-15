# Task Classification Rules

Tasks are classified into three levels: **L0**, **L1**, **L2**.
The level determines role involvement and verification rigor.

## Principle: Only Upgrade, Never Downgrade

If any indicator points to a higher level, use the higher level.
A task may only be reclassified downward by explicit `--force-l0/l1/l2` override with a stated reason.

## Level Definitions

| Level | Name | Description |
|---|---|---|
| L0 | Micro-task | Copy changes, small style fixes, isolated low-risk bug fixes |
| L1 | Normal task | New page/endpoint, one API, small scoped module change |
| L2 | High-risk task | Data model changes, architecture migration, auth/payment/sync |

## Heuristic Indicators

### L0 indicators

- Change touches only documentation, comments, or string literals
- Change touches only presentation/styling with no logic involved
- Bug is isolated to a single function with no downstream effects
- No new files, no new dependencies, no cross-module impact

### L1 indicators

- Adds a new unit of functionality (endpoint, page, component, module)
- Modifies existing logic in one module
- Introduces at most one new dependency
- Has clear rollback by reverting a bounded set of files

### L2 indicators (any one triggers L2)

- Touches the data model, schema, or database migrations
- Changes authentication, authorization, or permission logic
- Modifies payment, billing, or financial calculation logic
- Modifies synchronization, concurrency, or distributed state logic
- Crosses three or more modules in a single coordinated change
- Introduces infrastructure changes (CI, deployment, secrets, env vars)

## Hard Keyword Triggers (auto-elevate to L2)

Any task description or spec containing these terms must be classified L2 or above.
No heuristic override applies — only `--force-l0/l1` can downgrade with a stated reason.

| Keyword Group | Examples |
|---|---|
| Data model | `migration`, `schema`, `database`, `data model`, `table`, `column`, `index` |
| Architecture | `architecture migration`, `refactor across`, `cross-module`, `monolith`, `extract service` |
| Auth/permissions | `auth`, `authentication`, `authorization`, `permission`, `role`, `access control`, `oauth`, `jwt` |
| Payment/billing | `payment`, `billing`, `invoice`, `charge`, `subscription`, `stripe`, `financial` |
| Sync/concurrency | `sync`, `synchronization`, `concurrent`, `lock`, `race condition`, `distributed`, `queue` |
| Infrastructure | `ci`, `cd`, `pipeline`, `deployment`, `secrets`, `environment variables`, `dockerfile`, `terraform` |

## `--force-*` Override

Any level can be overridden by the user or invoking role with an explicit flag:
- `--force-l0` / `--force-l1` / `--force-l2`

**Rules for override:**
1. The overriding party must state a reason (`--force-l0 "cosmetic doc fix, no code change"`).
2. Override reasons are recorded in the task trace.
3. Downgrading (e.g., L2 → L0) requires a reason that explicitly addresses each L2 trigger that would otherwise apply.

## Classification Display Requirement

At task start, the classifier must display:

```
Task level: L1
Reason: new API endpoint added; no keyword triggers; single module impact
Override: --force-l2 available to escalate
```

This display is non-optional. Silent classification is not permitted.
