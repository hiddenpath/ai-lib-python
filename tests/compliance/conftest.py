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


@pytest.fixture(scope="session")
def mock_http_url() -> str | None:
    """Optional mock HTTP URL for compliance tests that need to hit ai-protocol-mock."""
    return os.environ.get("MOCK_HTTP_URL")
