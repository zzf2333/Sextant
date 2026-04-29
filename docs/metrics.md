# Sextant Reviewer Health Metrics

This document defines the four metrics tracked by `sextant metrics`, explains their
purpose, their limitations, and when each warrants investigation.

**Core principle**: These metrics exist to detect *ritualization drift*, not to grade
humans or the LLM. A number outside the "watch range" is a signal to investigate the
reviewer prompt or task mix — not a score to report or optimize against. If these numbers
become targets, they stop being useful measurements.

---

## Metric Definitions

### 1. Non-empty `deletion_proposals` ratio

**What it measures**: Fraction of review sessions where `deletion_proposals` contains at
least one bullet item (i.e., the reviewer actually proposed something to delete).

**Formula**: `count(reviews where deletion_proposals ≠ "none") / total reviews`

**Why it matters**: The reviewer's primary job is Reduction-Review — finding what can be
removed. A reviewer that consistently writes `none` is either not doing the job or
working on tasks that genuinely have nothing to cut. The difference matters.

**Watch range**: Below 30% across 10+ tasks is a signal worth investigating.

**Caveat**: A high ratio is not automatically good. A reviewer that manufactures low-value
proposals to avoid writing `none` is worse than an honest `none`. This metric only tells
you *whether the proposal field is being used* — not whether the proposals are useful.
That judgment remains with you.

---

### 2. Reviewer rejection ratio

**What it measures**: Fraction of review sessions with verdict `changes-requested` or
`rejected`.

**Formula**: `count(reviews with verdict ∈ {changes-requested, rejected}) / total reviews`

**Why it matters**: A reviewer that approves everything is a rubber stamp. Some level of
rejection is expected — it means the review is doing real work.

**Watch range**: Below 10% across 10+ tasks suggests the reviewer may be systematically
approving without scrutiny. Above 80% suggests scope problems upstream (specs are too vague,
plans are too optimistic) — investigate the root cause, not the reviewer.

**Caveat**: This metric is highly sensitive to task mix. Complex L2 tasks should have higher
rejection rates than simple L0 tasks. Always filter by task level (`--task-level L1,L2`)
before drawing conclusions.

---

### 3. Tasks where all reviews have "none" proposals

**What it measures**: Fraction of *tasks* (not individual reviews) where every review in
the task pipeline has `deletion_proposals: none`.

**Formula**: `count(tasks where all reviews have none) / total tasks`

**Why it matters**: A single `none` is fine and expected on tight, well-scoped tasks. But
when *every* review across spec, plan, and build all say `none` on the same task, it
suggests the reviewer is in "approve and move on" mode for that task. Repeated across many
tasks, this is the early signal of reviewer ritualization.

**Watch range**: Above 50% across 10+ tasks is a signal to re-examine the reviewer prompt.

---

### 4. `blindspots_verification_ratio` (manual observation only)

This metric — the fraction of reviewer-identified blindspots that led to new tests or
verification being added — requires semantic matching between reviewer output and
subsequent code commits. This cannot be calculated mechanically without introducing
pseudo-AI analysis.

**How to observe manually**: After a task, check whether the reviewer's `verification_gaps`
led to actual test additions in the Build stage. Tally this periodically in a team retro.
It is not tracked by `sextant metrics`.

---

## Using `sextant metrics`

```
sextant metrics [--since=DAYS] [--task-level=LEVELS] [--json]
```

**Examples:**

```bash
# All-time across all levels
sextant metrics

# Last 30 days, L1 and L2 only
sextant metrics --since=30 --task-level=L1,L2

# Machine-readable for dashboards
sextant metrics --json
```

**When to run**: Periodically (e.g., after every 5-10 completed tasks) to check for drift.
Not on every task — the metrics need sample size to be meaningful.

## v0.1.0 Release Readiness

For v0.1.0, metrics are used together with the trace contract and dogfood report.
They are release gates, not long-term product targets.

| Signal | Threshold | How to verify |
|---|---:|---|
| Real dogfood tasks | >= 10 | Count real trace directories in `.sextant/traces/` |
| Closed-loop completion rate | >= 80% | Completed trace has `record.md` after the full artifact chain |
| Reviewer non-empty deletion proposal rate | >= 50% | `sextant metrics --since 30` |
| Verify first-pass rate | >= 60% | Manual dogfood table in `docs/dogfood.md` |
| Active bypass rate | <= 20% | `forced_level: true`, skip markers, or dogfood notes |
| Average stage duration | <= 90 seconds | `sextant tokens --since 30` when `usage.json` is recorded |

See `docs/trace-contract.md` for the structural definition of a complete trace and
`docs/dogfood.md` for the release evidence template.

---

## Interpretation guidance

| Observation | Likely cause | What to investigate |
|---|---|---|
| `non_empty_dp_ratio` < 20% | Reviewer prompt too lenient; tasks genuinely simple; reviewer gaming | Re-read reviewer.md persona; check task complexity |
| `reviewer_rejection_ratio` < 5% | Rubber-stamp mode; tasks well-scoped; reviewer too agreeable | Re-read reviewer.md hard constraints; check if reviewer sees full artifact |
| `consecutive_none_tasks` > 60% | Ritualization spreading; prompt drift; easy task batch | Review the last 5 tasks manually; look at actual `deletion_proposals` content |
| All metrics healthy but quality feels low | Mechanical compliance without substance | Metrics can't detect this — requires human spot-check of actual review content |

---

## What metrics cannot tell you

- Whether a `deletion_proposals` item was actually high-quality
- Whether the reviewer correctly identified the most important risks
- Whether `none` was honest or lazy (requires reading the artifact)
- Whether approved-with-conditions were substantive or trivial

These are qualitative judgments that remain with the human reviewer of the reviewer's work.
The metrics are a first-pass signal — they flag when something might be wrong. They cannot
confirm that something is right.
