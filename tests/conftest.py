"""Root pytest fixtures for ai-lib-python tests."""

from __future__ import annotations

import os

import pytest


@pytest.fixture(scope="session")
def mock_endpoints() -> dict[str, str]:
    """Provide mock server URLs for tests that use ai-protocol-mock.

    Reads MOCK_HTTP_URL and MOCK_MCP_URL from environment.
    Defaults: http://localhost:4010, http://localhost:4010/mcp
    """
    mock_http = os.getenv("MOCK_HTTP_URL", "http://localhost:4010")
    mock_mcp = os.getenv("MOCK_MCP_URL", "http://localhost:4010/mcp")
    return {"http": mock_http, "mcp": mock_mcp}


@pytest.fixture(scope="session")
def mock_base_url(mock_endpoints: dict[str, str]) -> str:
    """Base URL for HTTP mock (for AiClient.create(base_url=...))."""
    return mock_endpoints["http"]


@pytest.fixture(scope="session")
def mock_mcp_url(mock_endpoints: dict[str, str]) -> str:
    """URL for MCP mock endpoint."""
    return mock_endpoints["mcp"]


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "mockserver: mark test as requiring ai-protocol-mock server (skip if MOCK_HTTP_URL not set)",
    )
