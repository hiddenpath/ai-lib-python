"""Tests for connection pool module."""

import pytest

from ai_lib_python.transport import (
    ConnectionPool,
    PoolConfig,
    PoolStats,
)


class TestPoolConfig:
    """Tests for PoolConfig."""

    def test_default_config(self) -> None:
        """Test default configuration."""
        config = PoolConfig.default()
        assert config.max_connections == 100
        assert config.max_keepalive_connections == 20

    def test_high_throughput_config(self) -> None:
        """Test high throughput configuration."""
        config = PoolConfig.high_throughput()
        assert config.max_connections == 200
        assert config.max_keepalive_connections == 50

    def test_low_latency_config(self) -> None:
        """Test low latency configuration."""
        config = PoolConfig.low_latency()
        assert config.max_connections == 50
        assert config.connect_timeout == 5.0

    def test_to_httpx_limits(self) -> None:
        """Test conversion to httpx limits."""
        config = PoolConfig(
            max_connections=50,
            max_keepalive_connections=10,
        )
        limits = config.to_httpx_limits()

        assert limits.max_connections == 50
        assert limits.max_keepalive_connections == 10

    def test_to_httpx_timeout(self) -> None:
        """Test conversion to httpx timeout."""
        config = PoolConfig(
            connect_timeout=5.0,
            read_timeout=30.0,
            write_timeout=10.0,
            pool_timeout=15.0,
        )
        timeout = config.to_httpx_timeout()

        assert timeout.connect == 5.0
        assert timeout.read == 30.0
        assert timeout.write == 10.0
        assert timeout.pool == 15.0


class TestPoolStats:
    """Tests for PoolStats."""

    def test_avg_connection_time(self) -> None:
        """Test average connection time calculation."""
        stats = PoolStats()
        stats.connection_times = [0.1, 0.2, 0.3]

        # Average is 0.2 seconds = 200ms
        assert abs(stats.avg_connection_time_ms - 200.0) < 0.01

    def test_avg_connection_time_empty(self) -> None:
        """Test average with no samples."""
        stats = PoolStats()
        assert stats.avg_connection_time_ms == 0.0

    def test_to_dict(self) -> None:
        """Test dictionary conversion."""
        stats = PoolStats(
            total_connections_created=10,
            requests_total=100,
            requests_successful=95,
            requests_failed=5,
        )

        d = stats.to_dict()
        assert d["total_connections_created"] == 10
        assert d["requests_total"] == 100
        assert d["requests_successful"] == 95


class TestConnectionPool:
    """Tests for ConnectionPool."""

    @pytest.mark.asyncio
    async def test_get_client(self) -> None:
        """Test getting a client."""
        async with ConnectionPool(PoolConfig.default()) as pool:
            client = await pool.get_client(
                "openai",
                "https://api.openai.com",
            )
            assert client is not None

    @pytest.mark.asyncio
    async def test_same_client_reused(self) -> None:
        """Test same client is reused for same provider/URL."""
        async with ConnectionPool(PoolConfig.default()) as pool:
            client1 = await pool.get_client("openai", "https://api.openai.com")
            client2 = await pool.get_client("openai", "https://api.openai.com")
            assert client1 is client2

    @pytest.mark.asyncio
    async def test_different_providers_different_clients(self) -> None:
        """Test different providers get different clients."""
        async with ConnectionPool(PoolConfig.default()) as pool:
            client1 = await pool.get_client("openai", "https://api.openai.com")
            client2 = await pool.get_client("anthropic", "https://api.anthropic.com")
            assert client1 is not client2

    @pytest.mark.asyncio
    async def test_record_request(self) -> None:
        """Test recording requests."""
        pool = ConnectionPool()

        pool.record_request("openai", success=True)
        pool.record_request("openai", success=True)
        pool.record_request("openai", success=False)

        stats = pool.get_stats("openai")
        assert stats["openai"]["requests_total"] == 3
        assert stats["openai"]["requests_successful"] == 2
        assert stats["openai"]["requests_failed"] == 1

        await pool.close()

    @pytest.mark.asyncio
    async def test_get_active_providers(self) -> None:
        """Test getting active providers."""
        async with ConnectionPool() as pool:
            await pool.get_client("openai", "https://api.openai.com")
            await pool.get_client("anthropic", "https://api.anthropic.com")

            providers = pool.get_active_providers()
            assert "openai" in providers
            assert "anthropic" in providers

    @pytest.mark.asyncio
    async def test_close_client(self) -> None:
        """Test closing a specific client."""
        pool = ConnectionPool()

        await pool.get_client("openai", "https://api.openai.com")
        await pool.close_client("openai", "https://api.openai.com")

        # Getting again should create new client
        providers = pool.get_active_providers()
        assert "openai" not in providers

        await pool.close()

    @pytest.mark.asyncio
    async def test_pool_closed_error(self) -> None:
        """Test error when pool is closed."""
        pool = ConnectionPool()
        await pool.close()

        with pytest.raises(RuntimeError, match="closed"):
            await pool.get_client("openai", "https://api.openai.com")

    @pytest.mark.asyncio
    async def test_context_manager(self) -> None:
        """Test context manager usage."""
        async with ConnectionPool() as pool:
            assert not pool.is_closed
            client = await pool.get_client("openai", "https://api.openai.com")
            assert client is not None

        assert pool.is_closed
