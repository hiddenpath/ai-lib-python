#!/usr/bin/env python3
"""
Resilience patterns performance benchmarks.

Measures overhead of resilience patterns.
"""

import asyncio
import time
from typing import Any

from ai_lib_python.resilience import (
    Backpressure,
    BackpressureConfig,
    CircuitBreaker,
    CircuitBreakerConfig,
    RateLimiter,
    RateLimiterConfig,
    ResilientConfig,
    ResilientExecutor,
    RetryConfig,
    RetryPolicy,
)


async def noop_operation() -> str:
    """No-op operation for overhead measurement."""
    return "result"


async def benchmark_baseline(iterations: int = 10000) -> dict[str, Any]:
    """Benchmark baseline async operation."""
    start = time.perf_counter()
    for _ in range(iterations):
        await noop_operation()
    elapsed = time.perf_counter() - start

    return {
        "name": "Baseline (no resilience)",
        "iterations": iterations,
        "elapsed_seconds": elapsed,
        "throughput_ops": iterations / elapsed,
        "latency_us": (elapsed / iterations) * 1_000_000,
    }


async def benchmark_retry_policy(iterations: int = 10000) -> dict[str, Any]:
    """Benchmark retry policy overhead (no retries triggered)."""
    policy = RetryPolicy(RetryConfig(max_retries=3))

    start = time.perf_counter()
    for _ in range(iterations):
        await policy.execute(noop_operation)
    elapsed = time.perf_counter() - start

    return {
        "name": "RetryPolicy (no retries)",
        "iterations": iterations,
        "elapsed_seconds": elapsed,
        "throughput_ops": iterations / elapsed,
        "latency_us": (elapsed / iterations) * 1_000_000,
    }


async def benchmark_rate_limiter_unlimited(iterations: int = 10000) -> dict[str, Any]:
    """Benchmark rate limiter overhead (unlimited)."""
    limiter = RateLimiter(RateLimiterConfig.unlimited())

    start = time.perf_counter()
    for _ in range(iterations):
        await limiter.acquire()
        await noop_operation()
    elapsed = time.perf_counter() - start

    return {
        "name": "RateLimiter (unlimited)",
        "iterations": iterations,
        "elapsed_seconds": elapsed,
        "throughput_ops": iterations / elapsed,
        "latency_us": (elapsed / iterations) * 1_000_000,
    }


async def benchmark_rate_limiter_high_limit(iterations: int = 1000) -> dict[str, Any]:
    """Benchmark rate limiter with high limit."""
    limiter = RateLimiter(RateLimiterConfig.from_rps(10000))  # Very high limit

    start = time.perf_counter()
    for _ in range(iterations):
        await limiter.acquire()
        await noop_operation()
    elapsed = time.perf_counter() - start

    return {
        "name": "RateLimiter (10k RPS)",
        "iterations": iterations,
        "elapsed_seconds": elapsed,
        "throughput_ops": iterations / elapsed,
        "latency_us": (elapsed / iterations) * 1_000_000,
    }


async def benchmark_circuit_breaker(iterations: int = 10000) -> dict[str, Any]:
    """Benchmark circuit breaker overhead (closed state)."""
    breaker = CircuitBreaker(CircuitBreakerConfig())

    start = time.perf_counter()
    for _ in range(iterations):
        await breaker.execute(noop_operation)
    elapsed = time.perf_counter() - start

    return {
        "name": "CircuitBreaker (closed)",
        "iterations": iterations,
        "elapsed_seconds": elapsed,
        "throughput_ops": iterations / elapsed,
        "latency_us": (elapsed / iterations) * 1_000_000,
    }


async def benchmark_backpressure_unlimited(iterations: int = 10000) -> dict[str, Any]:
    """Benchmark backpressure overhead (unlimited)."""
    bp = Backpressure(BackpressureConfig.unlimited())

    start = time.perf_counter()
    for _ in range(iterations):
        async with bp.acquire():
            await noop_operation()
    elapsed = time.perf_counter() - start

    return {
        "name": "Backpressure (unlimited)",
        "iterations": iterations,
        "elapsed_seconds": elapsed,
        "throughput_ops": iterations / elapsed,
        "latency_us": (elapsed / iterations) * 1_000_000,
    }


async def benchmark_backpressure_limited(iterations: int = 10000) -> dict[str, Any]:
    """Benchmark backpressure overhead (limited)."""
    bp = Backpressure(BackpressureConfig(max_concurrent=100))

    start = time.perf_counter()
    for _ in range(iterations):
        async with bp.acquire():
            await noop_operation()
    elapsed = time.perf_counter() - start

    return {
        "name": "Backpressure (100 concurrent)",
        "iterations": iterations,
        "elapsed_seconds": elapsed,
        "throughput_ops": iterations / elapsed,
        "latency_us": (elapsed / iterations) * 1_000_000,
    }


async def benchmark_resilient_executor_minimal(iterations: int = 10000) -> dict[str, Any]:
    """Benchmark resilient executor with minimal config."""
    executor = ResilientExecutor(ResilientConfig.minimal())

    start = time.perf_counter()
    for _ in range(iterations):
        await executor.execute(noop_operation)
    elapsed = time.perf_counter() - start

    return {
        "name": "ResilientExecutor (minimal)",
        "iterations": iterations,
        "elapsed_seconds": elapsed,
        "throughput_ops": iterations / elapsed,
        "latency_us": (elapsed / iterations) * 1_000_000,
    }


async def benchmark_resilient_executor_production(iterations: int = 1000) -> dict[str, Any]:
    """Benchmark resilient executor with production config."""
    executor = ResilientExecutor(ResilientConfig.production())

    start = time.perf_counter()
    for _ in range(iterations):
        await executor.execute(noop_operation)
    elapsed = time.perf_counter() - start

    return {
        "name": "ResilientExecutor (production)",
        "iterations": iterations,
        "elapsed_seconds": elapsed,
        "throughput_ops": iterations / elapsed,
        "latency_us": (elapsed / iterations) * 1_000_000,
    }


async def benchmark_concurrent_execution(
    concurrency: int = 100, iterations: int = 1000
) -> dict[str, Any]:
    """Benchmark concurrent execution with backpressure."""
    bp = Backpressure(BackpressureConfig(max_concurrent=concurrency))

    async def task() -> None:
        async with bp.acquire():
            await noop_operation()

    start = time.perf_counter()
    tasks = [task() for _ in range(iterations)]
    await asyncio.gather(*tasks)
    elapsed = time.perf_counter() - start

    return {
        "name": f"Concurrent ({concurrency} parallel)",
        "iterations": iterations,
        "elapsed_seconds": elapsed,
        "throughput_ops": iterations / elapsed,
        "latency_us": (elapsed / iterations) * 1_000_000,
        "peak_inflight": bp._peak_inflight,
    }


async def run_benchmarks() -> None:
    """Run all benchmarks and print results."""
    print("=" * 60)
    print("Resilience Benchmarks")
    print("=" * 60)
    print()

    benchmarks = [
        benchmark_baseline,
        benchmark_retry_policy,
        benchmark_rate_limiter_unlimited,
        benchmark_rate_limiter_high_limit,
        benchmark_circuit_breaker,
        benchmark_backpressure_unlimited,
        benchmark_backpressure_limited,
        benchmark_resilient_executor_minimal,
        benchmark_resilient_executor_production,
    ]

    baseline_latency = 0.0

    for bench in benchmarks:
        result = await bench()
        if result["name"].startswith("Baseline"):
            baseline_latency = result["latency_us"]

        overhead = ""
        if baseline_latency > 0 and not result["name"].startswith("Baseline"):
            overhead_us = result["latency_us"] - baseline_latency
            overhead_pct = (overhead_us / baseline_latency) * 100
            overhead = f" (+{overhead_us:.2f}µs, +{overhead_pct:.1f}%)"

        print(f"{result['name']}:")
        print(f"  Throughput: {result['throughput_ops']:.0f} ops/sec")
        print(f"  Latency: {result['latency_us']:.2f} µs/op{overhead}")
        print()

    # Concurrent benchmark
    print("Concurrent Execution:")
    for concurrency in [10, 50, 100]:
        result = await benchmark_concurrent_execution(concurrency=concurrency)
        print(f"  {concurrency} parallel: {result['throughput_ops']:.0f} ops/sec")


if __name__ == "__main__":
    asyncio.run(run_benchmarks())
