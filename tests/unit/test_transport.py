"""Tests for transport module."""

import os
from unittest.mock import patch

from ai_lib_python.protocol.manifest import AuthConfig, EndpointConfig, ProtocolManifest
from ai_lib_python.transport.auth import get_auth_header, resolve_api_key


class TestResolveApiKey:
    """Tests for API key resolution."""

    def test_explicit_key(self) -> None:
        """Test explicit API key takes precedence."""
        key = resolve_api_key("openai", explicit_key="sk-explicit")
        assert key == "sk-explicit"

    def test_env_variable_standard(self) -> None:
        """Test standard environment variable."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-env"}):
            key = resolve_api_key("openai")
            assert key == "sk-env"

    def test_env_variable_from_manifest(self) -> None:
        """Test environment variable from manifest config."""
        manifest = ProtocolManifest(
            id="custom",
            endpoint=EndpointConfig(base_url="https://example.com"),
            auth=AuthConfig(type="bearer", token_env="CUSTOM_TOKEN"),
        )
        with patch.dict(os.environ, {"CUSTOM_TOKEN": "sk-custom"}):
            key = resolve_api_key("custom", manifest=manifest)
            assert key == "sk-custom"

    def test_no_key_found(self) -> None:
        """Test when no key is found."""
        with patch.dict(os.environ, {}, clear=True):
            key = resolve_api_key("nonexistent")
            assert key is None


class TestGetAuthHeader:
    """Tests for auth header generation."""

    def test_bearer_auth(self) -> None:
        """Test bearer authentication header."""
        manifest = ProtocolManifest(
            id="test",
            endpoint=EndpointConfig(base_url="https://example.com"),
            auth=AuthConfig(type="bearer"),
        )
        headers = get_auth_header("test", manifest, api_key="sk-test")
        assert headers == {"Authorization": "Bearer sk-test"}

    def test_api_key_auth(self) -> None:
        """Test API key authentication header."""
        manifest = ProtocolManifest(
            id="test",
            endpoint=EndpointConfig(base_url="https://example.com"),
            auth=AuthConfig(type="api_key"),
        )
        headers = get_auth_header("test", manifest, api_key="key-123")
        assert headers == {"X-API-Key": "key-123"}

    def test_custom_header_name(self) -> None:
        """Test custom header name."""
        manifest = ProtocolManifest(
            id="test",
            endpoint=EndpointConfig(base_url="https://example.com"),
            auth=AuthConfig(type="bearer", header_name="X-Custom-Auth"),
        )
        headers = get_auth_header("test", manifest, api_key="sk-test")
        assert headers == {"X-Custom-Auth": "Bearer sk-test"}

    def test_no_key(self) -> None:
        """Test when no key is available."""
        with patch.dict(os.environ, {}, clear=True):
            headers = get_auth_header("nonexistent")
            assert headers == {}
