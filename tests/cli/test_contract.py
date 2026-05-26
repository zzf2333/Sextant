"""Tests for cli.contract — task contract generation and parsing."""
from __future__ import annotations
import tempfile
from pathlib import Path

from cli.contract import (
    TaskContract,
    parse_contract,
    generate_contract,
)


class TestTaskContract:
    """TaskContract dataclass tests."""

    def test_default_values(self):
        c = TaskContract(task_id="test-1")
        assert c.task_id == "test-1"
        assert c.task_type == "implementation"
        assert c.depends_on == []
        assert not c.parallelizable
        assert c.independent_verification

    def test_to_markdown_contains_sections(self):
        c = TaskContract(
            task_id="feat-x",
            task_type="implementation",
            objective="Build feature X",
            allowed_paths=["src/x/**", "tests/x/**"],
            forbidden_paths=["src/y/**"],
            constraints=["No new deps"],
            acceptance=["npm test"],
            review_focus=["race conditions"],
        )
        md = c.to_markdown()
        assert "# TASK_CONTRACT" in md
        assert "feat-x" in md
        assert "Build feature X" in md
        assert "src/x/**" in md
        assert "src/y/**" in md
        assert "No new deps" in md
        assert "npm test" in md
        assert "race conditions" in md
        assert "allowed_paths" in md
        assert "forbidden_paths" in md

    def test_validate_valid_contract(self):
        c = TaskContract(
            task_id="valid-task",
            task_type="implementation",
            objective="Do something",
            allowed_paths=["src/**"],
            acceptance=["npm test"],
        )
        errors = c.validate()
        assert errors == []

    def test_validate_missing_objective(self):
        c = TaskContract(
            task_id="no-obj",
            allowed_paths=["src/**"],
            acceptance=["npm test"],
        )
        errors = c.validate()
        assert any("objective" in e.lower() for e in errors)

    def test_validate_missing_allowed_paths(self):
        c = TaskContract(
            task_id="no-paths",
            objective="Do stuff",
            acceptance=["npm test"],
        )
        errors = c.validate()
        assert any("allowed_paths" in e.lower() for e in errors)

    def test_validate_missing_acceptance(self):
        c = TaskContract(
            task_id="no-accept",
            objective="Do stuff",
            allowed_paths=["src/**"],
        )
        errors = c.validate()
        assert any("acceptance" in e.lower() for e in errors)

    def test_validate_foundation_cannot_be_parallel(self):
        c = TaskContract(
            task_id="foundation-task",
            task_type="foundation",
            objective="Define API",
            allowed_paths=["src/api/**"],
            acceptance=["npm test"],
            parallelizable=True,
        )
        errors = c.validate()
        assert any("foundation" in e.lower() for e in errors)
        assert any("parallelizable" in e.lower() for e in errors)

    def test_validate_integration_cannot_independent_verify(self):
        c = TaskContract(
            task_id="integ-task",
            task_type="integration",
            objective="E2E tests",
            allowed_paths=["tests/**"],
            acceptance=["npm run e2e"],
            independent_verification=True,
        )
        errors = c.validate()
        assert any("integration" in e.lower() for e in errors)
        assert any("independent_verification" in e.lower() for e in errors)

    def test_validate_placeholder_objective_rejected(self):
        c = TaskContract(
            task_id="placeholder",
            objective="<!-- one-line description -->",
            allowed_paths=["src/**"],
            acceptance=["npm test"],
        )
        errors = c.validate()
        assert any("objective" in e.lower() for e in errors)

    def test_validate_bad_task_type(self):
        c = TaskContract(
            task_id="bad-type",
            task_type="unknown",
            objective="Stuff",
            allowed_paths=["src/**"],
            acceptance=["npm test"],
        )
        errors = c.validate()
        assert any("foundation/implementation/integration" in e.lower() for e in errors)


class TestContractParsing:
    """Contract parse/generate round-trip tests."""

    def test_generate_and_parse(self):
        c = TaskContract(
            task_id="roundtrip",
            task_type="implementation",
            objective="Test round trip",
            allowed_paths=["src/lib/**"],
            forbidden_paths=["src/secret/**"],
            constraints=["Keep it simple"],
            acceptance=["cargo test"],
            review_focus=["Performance"],
        )
        md = c.to_markdown()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(md)
            f.flush()
            parsed = parse_contract(Path(f.name))

        assert parsed is not None
        assert parsed.task_id == "roundtrip"
        assert parsed.task_type == "implementation"
        assert parsed.objective == "Test round trip"
        assert "src/lib/**" in parsed.allowed_paths
        assert "src/secret/**" in parsed.forbidden_paths
        assert "Keep it simple" in parsed.constraints
        assert "cargo test" in parsed.acceptance

    def test_parse_nonexistent_file(self):
        result = parse_contract(Path("/nonexistent/path.md"))
        assert result is None

    def test_generate_contract_helper(self):
        md = generate_contract(
            "gen-task",
            task_type="foundation",
            objective="Generate test",
            allowed_paths=["pkg/**"],
            acceptance=["go test ./..."],
        )
        assert "gen-task" in md
        assert "foundation" in md
        assert "Generate test" in md
        assert "pkg/**" in md
        assert "go test ./..." in md

    def test_depends_on_parsed(self):
        c = TaskContract(
            task_id="dep-task",
            objective="Dep task",
            allowed_paths=["src/**"],
            acceptance=["make test"],
            depends_on=["base-task", "api-task"],
        )
        md = c.to_markdown()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(md)
            f.flush()
            parsed = parse_contract(Path(f.name))

        assert parsed is not None
        assert "base-task" in parsed.depends_on
        assert "api-task" in parsed.depends_on
