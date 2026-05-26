"""
Task contract generation and validation.

A TASK_CONTRACT.md defines the bounded context for a single Executor Worker:
  - objective: what to build
  - allowed_paths / forbidden_paths: file system boundaries
  - constraints: hard limits
  - acceptance: verifiable completion criteria
  - review_focus: areas for Reviewer scrutiny
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

from cli.parsers import parse_frontmatter, parse_section


CONTRACT_TEMPLATE_PATH = Path(__file__).parent.parent / "core" / "templates" / "task-contract.md"


@dataclass
class TaskContract:
    task_id: str
    task_type: str = "implementation"  # foundation | implementation | integration
    depends_on: list[str] = field(default_factory=list)
    parallelizable: bool = False
    independent_verification: bool = True
    objective: str = ""
    allowed_paths: list[str] = field(default_factory=list)
    forbidden_paths: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    dependencies: list[dict] = field(default_factory=list)
    acceptance: list[str] = field(default_factory=list)
    review_focus: list[str] = field(default_factory=list)

    def to_markdown(self) -> str:
        """Render contract to TASK_CONTRACT.md format."""
        deps = self.depends_on if self.depends_on else []
        deps_str = "[" + ", ".join(deps) + "]" if deps else "[]"
        allowed_str = "\n".join(f"  - {p}" for p in (self.allowed_paths or ["<path>/**"]))
        forbidden_str = "\n".join(f"  - {p}" for p in (self.forbidden_paths or []))
        constraints_str = "\n".join(f"- {c}" for c in (self.constraints or ["<constraint>"]))
        ext_deps_str = "\n".join(
            f"  - name: {d.get('name', '')}\n    version: \"{d.get('version', '')}\""
            for d in self.dependencies
        ) if self.dependencies else "  - []"
        acceptance_str = "\n".join(f"- [ ] {c}" for c in (self.acceptance or ["<criterion>"]))
        review_str = "\n".join(f"- {f}" for f in (self.review_focus or ["<focus area>"]))

        return f"""# TASK_CONTRACT

## Metadata

```yaml
task_id: "{self.task_id}"
task_type: "{self.task_type}"
depends_on: {deps_str}
parallelizable: {str(self.parallelizable).lower()}
independent_verification: {str(self.independent_verification).lower()}
```

---

## objective

{self.objective or '<!-- one-line description -->'}

---

## allowed_paths

```yaml
allowed_paths:
{allowed_str}
```

---

## forbidden_paths

```yaml
forbidden_paths:
{forbidden_str}
```

---

## constraints

{constraints_str}

---

## dependencies

```yaml
dependencies:
{ext_deps_str}
```

---

## acceptance

{acceptance_str}

---

## review_focus

{review_str}
"""

    def validate(self) -> list[str]:
        """Validate the contract. Returns a list of validation errors (empty = valid)."""
        errors: list[str] = []

        if not self.task_id.strip():
            errors.append("task_id is required")

        if self.task_type not in ("foundation", "implementation", "integration"):
            errors.append(f"task_type must be foundation/implementation/integration, got '{self.task_type}'")

        if not self.objective.strip() or self.objective.startswith("<!--"):
            errors.append("objective is required and must not be a placeholder")

        if not self.allowed_paths:
            errors.append("allowed_paths is required (at least one path)")

        if not self.acceptance or all(
            c.startswith("<") for c in self.acceptance
        ):
            errors.append("at least one acceptance criterion is required")

        # Foundation tasks cannot be parallelized
        if self.task_type == "foundation" and self.parallelizable:
            errors.append("foundation tasks cannot be parallelizable")

        # Integration tasks cannot have independent verification
        if self.task_type == "integration" and self.independent_verification:
            errors.append("integration tasks cannot have independent_verification=true")

        return errors


def parse_contract(path: Path) -> Optional[TaskContract]:
    """Parse a TASK_CONTRACT.md file into a TaskContract."""
    try:
        text = path.read_text(encoding="utf-8")
    except (FileNotFoundError, OSError):
        return None

    # Parse the fenced YAML block in the Metadata section
    fm = _parse_metadata_yaml(text)

    # Parse YAML lists in allowed_paths and forbidden_paths sections
    allowed = _parse_yaml_list(parse_section(text, "allowed_paths") or "")
    forbidden = _parse_yaml_list(parse_section(text, "forbidden_paths") or "")

    # Parse constraints as bullet list
    constraints = _parse_bullet_list(parse_section(text, "constraints") or "")

    # Parse acceptance as checklist
    acceptance_section = parse_section(text, "acceptance") or ""
    acceptance = _parse_checklist(acceptance_section)

    # Parse review_focus as bullet list
    review_focus = _parse_bullet_list(parse_section(text, "review_focus") or "")

    return TaskContract(
        task_id=str(fm.get("task_id", path.parent.name)),
        task_type=str(fm.get("task_type", "implementation")),
        depends_on=fm.get("depends_on", []),
        parallelizable=bool(fm.get("parallelizable", False)),
        independent_verification=bool(fm.get("independent_verification", True)),
        objective=_extract_objective(text),
        allowed_paths=allowed,
        forbidden_paths=forbidden,
        constraints=constraints,
        dependencies=[],  # complex struct — skip for MVP
        acceptance=acceptance,
        review_focus=review_focus,
    )


def _parse_metadata_yaml(text: str) -> dict:
    """Parse the Metadata section's fenced YAML block in TASK_CONTRACT.md."""
    section = parse_section(text, "Metadata")
    if section is None:
        return {}

    # Find the fenced ```yaml block
    import re
    match = re.search(r'```yaml\s*\n(.*?)\n```', section, re.DOTALL)
    if not match:
        # Try without language specifier
        match = re.search(r'```\s*\n(.*?)\n```', section, re.DOTALL)
    if not match:
        return {}

    yaml_text = match.group(1)
    result: dict = {}
    for line in yaml_text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, raw = line.partition(":")
        value = raw.split("#")[0].strip().strip('"').strip("'")
        key = key.strip()

        # Handle depends_on list
        if key == "depends_on":
            if value == "[]" or value == "":
                result[key] = []
            else:
                # Parse inline list: [a, b] or a, b
                items = value.strip("[]").split(",")
                result[key] = [i.strip().strip('"').strip("'") for i in items if i.strip()]
        elif value.lower() == "true":
            result[key] = True
        elif value.lower() == "false":
            result[key] = False
        else:
            result[key] = value

    return result


def _parse_yaml_list(section: str) -> list[str]:
    """Parse a YAML-style list from a markdown section."""
    items: list[str] = []
    in_yaml = False
    for line in section.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_yaml = not in_yaml
            continue
        if in_yaml or stripped.startswith("- "):
            item = stripped.lstrip("-").strip()
            # Skip the key line (e.g., "allowed_paths:")
            if item.endswith(":") and not item.startswith("- "):
                continue
            if item and not item.startswith("#"):
                items.append(item)
    return items


def _parse_bullet_list(section: str) -> list[str]:
    """Parse a markdown bullet list."""
    items: list[str] = []
    for line in section.splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            item = stripped[2:].strip()
            if item and not item.startswith("<!--"):
                items.append(item)
    return items


def _parse_checklist(section: str) -> list[str]:
    """Parse a markdown checklist into criteria strings."""
    items: list[str] = []
    for line in section.splitlines():
        stripped = line.strip()
        if stripped.startswith("- [ ]"):
            item = stripped[5:].strip()
            if item and not item.startswith("<!--"):
                items.append(item)
        elif stripped.startswith("- [x]") or stripped.startswith("- [X]"):
            pass  # already completed — skip
    return items


def _extract_objective(text: str) -> str:
    """Extract the objective from a TASK_CONTRACT.md."""
    section = parse_section(text, "objective")
    if section is None:
        return ""
    # Return the first non-comment, non-empty line
    for line in section.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("<!--") and not stripped.startswith(">"):
            return stripped
    return ""


def generate_contract(task_id: str, **kwargs) -> str:
    """Generate a TASK_CONTRACT.md from parameters."""
    contract = TaskContract(task_id=task_id, **kwargs)
    return contract.to_markdown()
