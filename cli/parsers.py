"""
Shared parsers for Sextant trace artifacts.
Handles yaml frontmatter extraction and markdown section parsing.
No third-party dependencies — stdlib only.
"""
from __future__ import annotations
import re
from pathlib import Path
from typing import Any


def _coerce(value: str) -> Any:
    """Coerce a raw YAML scalar string to Python str / int / bool."""
    stripped = value.strip().strip('"').strip("'")
    if stripped.lower() == "true":
        return True
    if stripped.lower() == "false":
        return False
    if re.fullmatch(r"\d+", stripped):
        return int(stripped)
    return stripped


def parse_frontmatter(text: str) -> dict[str, Any]:
    """Extract YAML-style frontmatter from a markdown string.

    Handles: string, int, bool scalar values.
    Does not handle nested objects or block lists — Sextant frontmatter
    only uses flat key: value pairs.
    """
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not match:
        return {}
    block = match.group(1)
    result: dict[str, Any] = {}
    for line in block.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, raw = line.partition(":")
        # Strip inline comment
        value_part = raw.split("#")[0].strip()
        result[key.strip()] = _coerce(value_part)
    return result


def parse_section(text: str, section_name: str) -> str | None:
    """Extract the body of a ## section_name from markdown.

    Returns the trimmed text between this heading and the next ## heading
    (or end of document). Returns None if the section is not found.
    """
    pattern = rf"^##\s+{re.escape(section_name)}\s*\n(.*?)(?=^##\s|\Z)"
    match = re.search(pattern, text, re.MULTILINE | re.DOTALL)
    if not match:
        return None
    return match.group(1).strip()


def extract_verdict(text: str) -> str | None:
    """Extract the verdict value from a review artifact's ## verdict section.

    Handles backtick-wrapped values (`approved`) and plain text.
    Ignores template residue like "`approved` | `approved-with-conditions` | `rejected`" —
    always returns the first non-pipe token.
    """
    section = parse_section(text, "verdict")
    if section is None:
        return None
    # Remove backticks, take first pipe-separated token
    token = section.strip().split("|")[0].strip().strip("`").strip()
    if not token:
        return None
    return token


def read_artifact(path: Path) -> tuple[dict[str, Any], str]:
    """Read a trace artifact file.

    Returns (frontmatter_dict, full_text).
    """
    text = path.read_text(encoding="utf-8")
    return parse_frontmatter(text), text
