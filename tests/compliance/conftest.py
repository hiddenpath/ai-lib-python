"""
Pytest fixtures for AI-Protocol compliance tests.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

# Default compliance directory: ai-protocol/tests/compliance (sibling repo)
_DEFAULT_COMPLIANCE = Path(__file__).resolve().parents[2] / ".." / ".." / "ai-protocol" / "tests" / "compliance"
COMPLIANCE_DIR = Path(
    os.environ.get(
        "COMPLIANCE_DIR",
        str(_DEFAULT_COMPLIANCE.resolve()),
    )
)


@pytest.fixture(scope="session")
def compliance_dir() -> Path:
    """Session fixture for the compliance test cases directory."""
    return COMPLIANCE_DIR
