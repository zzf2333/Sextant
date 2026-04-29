# Reviewer Context Boundary

Reviewer isolation is not zero context. A useful reviewer needs project facts and
the artifact under review. The boundary is about context type: facts are allowed;
author self-justification is not.

## Clean Context Packet

Every reviewer invocation must be built as a Clean Context Packet with three allowed
input groups and one explicit exclusion group.

### Allowed: Facts

Facts describe the current project world and must be independently checkable:

- current tech stack and runtime constraints
- module boundaries and existing file layout
- established project preferences from `.sextant/SEXTANT.md`
- relevant `modules/*/EVOLUTION.md` decisions
- rejected paths and durable project decisions from `.sextant/PROJECT_EVOLUTION_LOG.md`
- deterministic tool output, such as test, lint, typecheck, or hook results

### Allowed: Artifacts

Artifacts are formal stage outputs, not process transcripts:

- `spec.md`
- `plan.md`
- `build-summary.md`
- build diff
- verification output

### Allowed: Rubric

Rubric tells the reviewer how to judge the artifact:

- `core/roles/reviewer.md`
- `core/templates/review.md`
- the current review stage: `spec`, `plan`, or `build`
- stage-specific gate requirements

### Forbidden: Contaminating Context

Do not include context whose purpose is to persuade the reviewer that the author was
right:

- generation transcripts from spec, planner, builder, or prior reviewer sessions
- hidden reasoning or thinking traces
- draft alternatives that were not selected
- author self-justification outside the formal artifact
- user-agent negotiation history
- prior reviewer prose except unresolved conditions that must be checked

## Boundary Test

If the information describes what the project currently is, it may enter the packet.
If the information explains why the author believes the artifact is right, exclude it.

## Contamination Handling

If a reviewer receives forbidden context, the review is contaminated. The reviewer must:

1. set `contamination_detected: true` in `context_boundary`
2. explain the contaminating input in `contamination_notes`
3. ignore the contaminating input where possible
4. return `rejected` if the clean packet is insufficient for a trustworthy review
