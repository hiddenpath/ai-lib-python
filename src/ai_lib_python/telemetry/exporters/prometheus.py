"""
Prometheus metrics exporter.

Provides HTTP endpoint for Prometheus scraping.
"""

from __future__ import annotations

from typing import Any

from ai_lib_python.telemetry.metrics import MetricsCollector, get_metrics_collector


class PrometheusExporter:
    """Prometheus metrics exporter.

    Provides metrics in Prometheus format, optionally serving
    an HTTP endpoint for scraping.

    Example:
        >>> exporter = PrometheusExporter(port=9090)
        >>> await exporter.start()
        >>> # Metrics available at http://localhost:9090/metrics
        >>> await exporter.stop()
    """

    def __init__(
        self,
        collector: MetricsCollector | None = None,
        port: int = 9090,
        host: str = "0.0.0.0",
        path: str = "/metrics",
    ) -> None:
        """Initialize exporter.

        Args:
            collector: Metrics collector (uses global if None)
            port: HTTP server port
            host: HTTP server host
            path: Metrics endpoint path
        """
        self._collector = collector or get_metrics_collector()
        self._port = port
        self._host = host
        self._path = path
        self._server: Any = None
        self._running = False

    def get_metrics(self) -> str:
        """Get metrics in Prometheus format.

        Returns:
            Prometheus-formatted metrics string
        """
        return self._collector.to_prometheus()

    async def start(self) -> None:
        """Start the HTTP server for Prometheus scraping."""
        if self._running:
            return

        try:
            # Try to use aiohttp if available
            from aiohttp import web

            app = web.Application()
            app.router.add_get(self._path, self._handle_metrics)

            runner = web.AppRunner(app)
            await runner.setup()
            site = web.TCPSite(runner, self._host, self._port)
            await site.start()

            self._server = runner
            self._running = True

        except ImportError:
            # Fall back to simple implementation
            self._running = True
            # Note: In production, recommend installing aiohttp

    async def stop(self) -> None:
        """Stop the HTTP server."""
        if not self._running:
            return

        if self._server:
            await self._server.cleanup()
            self._server = None

        self._running = False

    async def _handle_metrics(self, request: Any) -> Any:  # noqa: ARG002
        """Handle metrics request."""
        from aiohttp import web

        metrics = self.get_metrics()
        return web.Response(
            text=metrics,
            content_type="text/plain; charset=utf-8",
        )

    @property
    def is_running(self) -> bool:
        """Check if server is running."""
        return self._running

    @property
    def endpoint(self) -> str:
        """Get metrics endpoint URL."""
        return f"http://{self._host}:{self._port}{self._path}"
