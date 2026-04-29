# Review Template

Use this template to record the output of the `reviewer` role.
Every field is mandatory. See `core/roles/reviewer.md` for role constraints.

---

## Metadata

```yaml
stage: spec | plan | build          # which stage produced the artifact being reviewed
reviewed_artifact_ref: ""           # path or identifier of the upstream artifact
reviewer_session_id: ""             # a short unique id for this review session (e.g. task-id + stage)
review_version: 1                   # increment when resubmitting after the upstream artifact changes
```

---

## context_boundary

```yaml
packet_type: clean_context_packet
contamination_detected: false
contamination_notes: none
missing_facts: none
```

Set `contamination_detected: true` if the review input included generation transcript,
hidden reasoning, author self-justification, or user-agent negotiation history. When true,
`contamination_notes` must explain what contaminated the packet.

---

## deletion_proposals

> **MANDATORY.** List every element that could be removed without affecting the outcome.
> If nothing qualifies for deletion, write `none` — do not leave this section empty or omit it.

<!--
Examples:
- "spec.constraints[2]: the 'no external dependencies' constraint is already implied by SEXTANT.md — remove the duplicate"
- "plan.candidates[1]: the Redis option adds a new dependency for a use case that a simple map handles — delete candidate"
- none
-->

`none`

---

## complexity_smells

> List abstraction layers, interfaces, or indirections not earned by current requirements.
> Empty list `[]` is a valid result.

- <!-- smell 1 -->

---

## verification_gaps

> List claims in the artifact that are asserted by trust but not verified by a tool, test, or
> checkable criterion. Empty list `[]` is a valid result.

- <!-- gap 1 -->

---

## verdict

`approved` | `approved-with-conditions` | `rejected`

---

## conditions

> Required if verdict is `approved-with-conditions` or `rejected`.
> List each condition the upstream role must resolve before resubmitting.
> Empty list `[]` if verdict is `approved`.

- <!-- condition 1 -->
