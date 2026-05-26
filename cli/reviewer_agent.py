"""
Automated review gate — invokes an LLM reviewer with a Clean Context Packet.

Produces a REVIEW.md artifact that can be parsed and validated.
The reviewer receives only facts + artifacts + rubric — no author self-justification.

Supports configurable review backends:
  - claude: invoke via Claude CLI
  - codex: invoke via Codex CLI
  - file: write prompt to file for manual review
"""
from __future__ import annotations
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from cli.contract import TaskContract, parse_contract
from cli.worktree import WorktreeInfo, get_worktree_info
from cli.validator import ValidationResult


# ── Data structures ───────────────────────────────────────────────────

@dataclass
class ReviewPacket:
    """Clean Context Packet for reviewer invocation."""
    task_id: str
    stage: str  # spec | plan | build
    facts: list[str] = field(default_factory=list)
    artifacts: dict[str, str] = field(default_factory=dict)  # name -> path
    rubric_paths: list[str] = field(default_factory=list)
    verification_summary: Optional[str] = None


@dataclass
class ReviewResult:
    task_id: str
    review_path: Optional[Path] = None
    verdict: Optional[str] = None
    deletion_proposals: list[str] = field(default_factory=list)
    conditions: list[str] = field(default_factory=list)
    complexity_smells: list[str] = field(default_factory=list)
    verification_gaps: list[str] = field(default_factory=list)
    context_boundary_clean: bool = True
    contamination_notes: str = ""
    raw_output: str = ""


# ── Packet builder ────────────────────────────────────────────────────

def build_review_packet(
    task_id: str,
    stage: str,
    contract: TaskContract,
    worktree: Optional[WorktreeInfo] = None,
    verify_result: Optional[ValidationResult] = None,
    traces_dir: Optional[Path] = None,
) -> ReviewPacket:
    """Build a Clean Context Packet for reviewer invocation.

    Contains only allowed inputs:
      - Facts: project state, contract, constraints
      - Artifacts: formal outputs under review
      - Rubric: reviewer role prompt and template
    Excludes:
      - Author self-justification
      - Generation transcripts
      - Negotiation history
    """
    packet = ReviewPacket(task_id=task_id, stage=stage)

    # Facts
    packet.facts.append(f"Task ID: {task_id}")
    packet.facts.append(f"Review stage: {stage}")
    packet.facts.append(f"Objective: {contract.objective}")
    packet.facts.append(f"Task type: {contract.task_type}")
    if contract.constraints:
        packet.facts.append("Constraints:")
        for c in contract.constraints:
            packet.facts.append(f"  - {c}")
    if contract.allowed_paths:
        packet.facts.append(f"Allowed paths: {', '.join(contract.allowed_paths)}")
    if contract.forbidden_paths:
        packet.facts.append(f"Forbidden paths: {', '.join(contract.forbidden_paths)}")

    # Acceptance criteria
    if contract.acceptance:
        packet.facts.append("Acceptance criteria:")
        for a in contract.acceptance:
            packet.facts.append(f"  - [ ] {a}")

    # Review focus hints
    if contract.review_focus:
        packet.facts.append("Review focus areas:")
        for f in contract.review_focus:
            packet.facts.append(f"  - {f}")

    # Artifacts: build diff if worktree exists
    if worktree and worktree.exists:
        diff = _get_worktree_diff(worktree.path)
        if diff:
            packet.artifacts["build_diff"] = diff

    # Verification results
    if verify_result:
        packet.verification_summary = _summarize_verification(verify_result)

    # Rubric: find role and template files
    sextant_root = Path(__file__).parent.parent
    reviewer_role = sextant_root / "core" / "roles" / "reviewer.md"
    review_template = sextant_root / "core" / "templates" / "review.md"
    context_boundary = sextant_root / "core" / "rules" / "reviewer-context-boundary.md"

    if reviewer_role.exists():
        packet.rubric_paths.append(str(reviewer_role))
    if review_template.exists():
        packet.rubric_paths.append(str(review_template))
    if context_boundary.exists():
        packet.rubric_paths.append(str(context_boundary))

    return packet


def _get_worktree_diff(wt_path: Path) -> str:
    """Get the git diff for a worktree."""
    try:
        result = subprocess.run(
            ["git", "diff", "main..."],
            cwd=wt_path,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        # Fallback
        result = subprocess.run(
            ["git", "diff", "HEAD~1" if _has_commits(wt_path) else "HEAD"],
            cwd=wt_path,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except Exception:
        return ""


def _has_commits(wt_path: Path) -> bool:
    try:
        subprocess.run(
            ["git", "rev-parse", "HEAD~1"],
            cwd=wt_path, capture_output=True, timeout=10,
        ).check_returncode()
        return True
    except subprocess.CalledProcessError:
        return False


def _summarize_verification(vr: ValidationResult) -> str:
    """Create a human-readable verification summary."""
    lines = [f"Verification {'PASSED' if vr.passed else 'FAILED'}", ""]
    for check in vr.checks:
        status = "PASS" if check["passed"] else "FAIL"
        lines.append(f"  [{status}] {check['name']}: {check['detail'][:100]}")
    return "\n".join(lines)


# ── Prompt builder ────────────────────────────────────────────────────

def build_review_prompt(packet: ReviewPacket) -> str:
    """Build the complete review prompt from a Clean Context Packet.

    This is the prompt sent to the LLM reviewer. It combines:
      1. The reviewer role (from core/roles/reviewer.md)
      2. The Clean Context Packet facts
      3. The artifacts under review
      4. The review template (output format)
      5. The context boundary rules
    """
    parts: list[str] = []

    # Role prompt
    sextant_root = Path(__file__).parent.parent
    reviewer_role_path = sextant_root / "core" / "roles" / "reviewer.md"
    if reviewer_role_path.exists():
        parts.append(reviewer_role_path.read_text(encoding="utf-8"))
    else:
        parts.append("# Role: reviewer\n\nReview the following artifact and produce a REVIEW.md.")

    parts.append("\n---\n")

    # Packet facts
    parts.append("# Clean Context Packet\n")
    for fact in packet.facts:
        parts.append(fact)
    parts.append("")

    # Verification
    if packet.verification_summary:
        parts.append("## Verification Results\n")
        parts.append(packet.verification_summary)
        parts.append("")

    # Artifacts
    if packet.artifacts:
        parts.append("## Artifacts Under Review\n")
        for name, content in packet.artifacts.items():
            parts.append(f"### {name}\n")
            if len(content) > 8000:
                parts.append(content[:8000])
                parts.append(f"\n\n... (truncated, {len(content)} total chars)")
            else:
                parts.append(content)
            parts.append("")

    # Output template
    review_template_path = sextant_root / "core" / "templates" / "review.md"
    if review_template_path.exists():
        parts.append("---\n")
        parts.append("## Output Format\n")
        parts.append("Produce a REVIEW.md using this template:\n")
        parts.append(review_template_path.read_text(encoding="utf-8"))

    # Reminders
    parts.append("---\n")
    parts.append("## Important Reminders\n")
    parts.append("1. `deletion_proposals` is MANDATORY — write `none` if nothing to delete")
    parts.append("2. `context_boundary` is MANDATORY — confirm the packet is clean")
    parts.append("3. Review scope matches stage — do not re-litigate earlier decisions")
    parts.append("4. Verdict must be one of: approved / approved-with-conditions / changes-requested / rejected")

    return "\n".join(parts)


# ── Review execution ──────────────────────────────────────────────────

def run_review(
    task_id: str,
    stage: str = "build",
    worktrees_dir: Optional[Path] = None,
    traces_dir: Optional[Path] = None,
    backend: str = "file",
    model: str = "claude-sonnet-4-6",
    output_dir: Optional[Path] = None,
) -> ReviewResult:
    """Execute a full review cycle.

    Args:
        task_id: Task identifier
        stage: Review stage (spec|plan|build)
        worktrees_dir: Worktrees directory
        traces_dir: Traces directory
        backend: Review backend (claude|codex|file)
        model: Model to use
        output_dir: Where to write REVIEW.md

    Returns:
        ReviewResult with verdict and details
    """
    result = ReviewResult(task_id=task_id)

    # Resolve paths
    if worktrees_dir is None:
        worktrees_dir = Path(".sextant-worktrees")
    if traces_dir is None:
        traces_dir = Path(".sextant/traces")
    if output_dir is None:
        output_dir = traces_dir / task_id

    # Load contract
    contract_path = traces_dir / task_id / "TASK_CONTRACT.md"
    if not contract_path.exists():
        contract_path = worktrees_dir / task_id / "TASK_CONTRACT.md"
    contract = parse_contract(contract_path)
    if contract is None:
        contract = TaskContract(task_id=task_id, objective="(no contract found)")

    # Get worktree
    wt = get_worktree_info(task_id, worktrees_dir)

    # Get verification results
    verify_result = None
    try:
        from cli.validator import validate_contract
        verify_result = validate_contract(task_id, worktrees_dir)
    except Exception:
        pass

    # Build packet
    packet = build_review_packet(
        task_id=task_id,
        stage=stage,
        contract=contract,
        worktree=wt,
        verify_result=verify_result,
        traces_dir=traces_dir,
    )

    # Build prompt
    prompt = build_review_prompt(packet)

    # Write prompt for traceability
    output_dir.mkdir(parents=True, exist_ok=True)
    prompt_path = output_dir / "REVIEW_PROMPT.md"
    prompt_path.write_text(prompt, encoding="utf-8")

    # Invoke reviewer
    if backend == "file":
        # Write prompt + instructions for manual review
        review_path = output_dir / "REVIEW.md"
        if not review_path.exists():
            review_path.write_text(
                _empty_review_template(task_id, stage), encoding="utf-8"
            )
        print(f"  Review prompt written to: {prompt_path}")
        print(f"  Review template at: {review_path}")
        print(f"  Copy the prompt to an LLM, fill the template, save REVIEW.md")
        result.review_path = review_path

    elif backend == "claude":
        review_path = _invoke_claude(prompt, output_dir)
        result.review_path = review_path

    elif backend == "codex":
        review_path = _invoke_codex(prompt, output_dir)
        result.review_path = review_path

    else:
        print(f"  Unknown backend: {backend}. Use 'file' backend for manual review.")

    # Parse the review if it exists
    if result.review_path and result.review_path.exists():
        _parse_review_output(result.review_path, result)

    return result


def _empty_review_template(task_id: str, stage: str) -> str:
    """Generate an empty REVIEW.md template."""
    return f"""# Review

## Metadata

```yaml
stage: "{stage}"
reviewed_artifact_ref: "{task_id}"
reviewer_session_id: ""
review_version: 1
```

---

## context_boundary

```yaml
packet_type: clean_context_packet
contamination_detected: false
contamination_notes: ""
missing_facts: ""
```

---

## deletion_proposals

none

---

## complexity_smells

- <!-- abstraction layers not earned by current requirements -->

---

## verification_gaps

- <!-- checks or tests missing -->

---

## verdict

`approved` | `approved-with-conditions` | `changes-requested` | `rejected`

---

## conditions

- <!-- required if verdict is not approved; empty list [] otherwise -->
"""


def _invoke_claude(prompt: str, output_dir: Path) -> Optional[Path]:
    """Invoke Claude CLI for review."""
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            f.write(prompt)
            prompt_file = f.name

        # Invoke Claude CLI
        result = subprocess.run(
            ["claude", "read", prompt_file, "--print"],
            capture_output=True,
            text=True,
            timeout=300,
        )

        if result.returncode != 0:
            print(f"  Claude invocation failed: {result.stderr[:200]}")
            return None

        review_path = output_dir / "REVIEW.md"
        review_path.write_text(result.stdout, encoding="utf-8")
        print(f"  Review written to: {review_path}")
        return review_path

    except FileNotFoundError:
        print("  Claude CLI not found. Install with: npm install -g @anthropic-ai/claude-code")
        return None
    except subprocess.TimeoutExpired:
        print("  Claude invocation timed out")
        return None
    finally:
        try:
            Path(prompt_file).unlink()
        except Exception:
            pass


def _invoke_codex(prompt: str, output_dir: Path) -> Optional[Path]:
    """Invoke Codex CLI for review."""
    print("  Codex backend not yet implemented. Use 'file' backend.")
    return None


def _parse_review_output(path: Path, result: ReviewResult) -> None:
    """Parse a REVIEW.md file to extract verdict and details."""
    from cli.parsers import parse_frontmatter, parse_section, extract_verdict

    try:
        text = path.read_text(encoding="utf-8")

        # Verdict
        result.verdict = extract_verdict(text) or "unknown"

        # Deletion proposals
        dp = parse_section(text, "deletion_proposals") or ""
        result.deletion_proposals = [
            l.strip("- ").strip()
            for l in dp.splitlines()
            if l.strip().startswith("-") and l.strip("- ").strip().lower() != "none"
        ]

        # Conditions
        cond = parse_section(text, "conditions") or ""
        result.conditions = [
            l.strip("- ").strip()
            for l in cond.splitlines()
            if l.strip().startswith("-") and "[]" not in l
        ]

        # Complexity smells
        cs = parse_section(text, "complexity_smells") or ""
        result.complexity_smells = [
            l.strip("- ").strip()
            for l in cs.splitlines()
            if l.strip().startswith("-") and "<!--" not in l
        ]

        # Verification gaps
        vg = parse_section(text, "verification_gaps") or ""
        result.verification_gaps = [
            l.strip("- ").strip()
            for l in vg.splitlines()
            if l.strip().startswith("-") and "<!--" not in l
        ]

        # Context boundary
        cb = parse_section(text, "context_boundary") or ""
        if "contamination_detected: true" in cb.lower():
            result.context_boundary_clean = False
            # Extract contamination notes
            for line in cb.splitlines():
                if "contamination_notes:" in line:
                    result.contamination_notes = line.split(":", 1)[1].strip().strip('"')
                    break

        result.raw_output = text

    except Exception as e:
        print(f"  Warning: could not parse review output: {e}")


def format_review_result(rr: ReviewResult) -> str:
    """Format a ReviewResult for display."""
    verdict_symbols = {
        "approved": "\u2713 APPROVED",
        "approved-with-conditions": "\u26a0 APPROVED WITH CONDITIONS",
        "changes-requested": "\u2717 CHANGES REQUESTED",
        "rejected": "\u2717 REJECTED",
        "unknown": "? PENDING",
    }
    symbol = verdict_symbols.get(
        rr.verdict.lower() if rr.verdict else "unknown",
        f"? {rr.verdict}"
    )

    lines = [
        f"Review: {rr.task_id}  [{symbol}]",
        "",
    ]

    if rr.deletion_proposals:
        lines.append(f"Deletion proposals: {len(rr.deletion_proposals)}")
        for dp in rr.deletion_proposals[:10]:
            lines.append(f"  - {dp}")
    else:
        lines.append("Deletion proposals: none")

    if rr.conditions:
        lines.append(f"Conditions: {len(rr.conditions)}")
        for c in rr.conditions:
            lines.append(f"  - {c}")

    if rr.complexity_smells:
        lines.append(f"Complexity smells: {len(rr.complexity_smells)}")
        for cs in rr.complexity_smells[:5]:
            lines.append(f"  - {cs}")

    if rr.verification_gaps:
        lines.append(f"Verification gaps: {len(rr.verification_gaps)}")

    if not rr.context_boundary_clean:
        lines.append("")
        lines.append(f"Context boundary: CONTAMINATED")
        lines.append(f"  Notes: {rr.contamination_notes}")

    return "\n".join(lines)
