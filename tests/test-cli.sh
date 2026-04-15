#!/usr/bin/env bash
# Run Python CLI tests (sextant status / lint / metrics) via pytest.
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if ! command -v python3 >/dev/null 2>&1; then
    echo "SKIP: python3 not found — skipping CLI tests"
    exit 0
fi

cd "$REPO_ROOT"

# Install package and pytest if not already available
if ! python3 -c "import cli" 2>/dev/null; then
    python3 -m pip install -e . --quiet
fi
if ! python3 -c "import pytest" 2>/dev/null; then
    python3 -m pip install pytest --quiet
fi

python3 -m pytest tests/cli/ -v
