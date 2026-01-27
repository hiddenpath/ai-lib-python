#!/usr/bin/env python3
"""
Pipeline performance benchmarks.

Measures throughput and latency of streaming pipeline components.
"""

import asyncio
import time
from typing import Any

from ai_lib_python.pipeline import (
    DefaultEventMapper,
    JsonLinesDecoder,
    JsonPathSelector,
    Pipeline,
    SSEDecoder,
)


async def generate_sse_chunks(count: int) -> list[bytes]:
    """Generate mock SSE chunks for benchmarking."""
    chunks = []
    for i in range(count):
        data = {
            "choices": [
                {
                    "delta": {"content": f"Token{i}"},
                    "index": 0,
                }
            ]
        }
        import json

        chunk = f"data: {json.dumps(data)}\n\n".encode()
        chunks.append(chunk)
    chunks.append(b"data: [DONE]\n\n")
    return chunks


async def benchmark_sse_decoder(iterations: int = 1000) -> dict[str, Any]:
    """Benchmark SSE decoder throughput."""
    chunks = await generate_sse_chunks(iterations)
    decoder = SSEDecoder()

    async def byte_stream():
        for chunk in chunks:
            yield chunk

    start = time.perf_counter()
    frames = []
    async for frame in decoder.decode(byte_stream()):
        frames.append(frame)
    elapsed = time.perf_counter() - start

    return {
        "name": "SSEDecoder",
        "iterations": iterations,
        "frames_decoded": len(frames),
        "elapsed_seconds": elapsed,
        "throughput_fps": len(frames) / elapsed,
        "latency_us": (elapsed / len(frames)) * 1_000_000,
    }


async def benchmark_json_lines_decoder(iterations: int = 1000) -> dict[str, Any]:
    """Benchmark JSON Lines decoder throughput."""
    import json

    chunks = []
    for i in range(iterations):
        data = {"id": i, "content": f"Token{i}"}
        chunks.append(json.dumps(data).encode() + b"\n")

    decoder = JsonLinesDecoder()

    async def byte_stream():
        for chunk in chunks:
            yield chunk

    start = time.perf_counter()
    frames = []
    async for frame in decoder.decode(byte_stream()):
        frames.append(frame)
    elapsed = time.perf_counter() - start

    return {
        "name": "JsonLinesDecoder",
        "iterations": iterations,
        "frames_decoded": len(frames),
        "elapsed_seconds": elapsed,
        "throughput_fps": len(frames) / elapsed,
        "latency_us": (elapsed / len(frames)) * 1_000_000,
    }


async def benchmark_selector(iterations: int = 1000) -> dict[str, Any]:
    """Benchmark JSONPath selector throughput."""
    selector = JsonPathSelector("exists($.choices)")

    frames = [
        {"choices": [{"delta": {"content": f"Token{i}"}}]}
        for i in range(iterations)
    ]

    async def frame_stream():
        for frame in frames:
            yield frame

    start = time.perf_counter()
    selected = []
    async for frame in selector.transform(frame_stream()):
        selected.append(frame)
    elapsed = time.perf_counter() - start

    return {
        "name": "JsonPathSelector",
        "iterations": iterations,
        "frames_selected": len(selected),
        "elapsed_seconds": elapsed,
        "throughput_fps": len(selected) / elapsed,
        "latency_us": (elapsed / len(selected)) * 1_000_000,
    }


async def benchmark_event_mapper(iterations: int = 1000) -> dict[str, Any]:
    """Benchmark event mapper throughput."""
    mapper = DefaultEventMapper()

    frames = [
        {"choices": [{"delta": {"content": f"Token{i}"}, "index": 0}]}
        for i in range(iterations)
    ]

    async def frame_stream():
        for frame in frames:
            yield frame

    start = time.perf_counter()
    events = []
    async for event in mapper.map_events(frame_stream()):
        events.append(event)
    elapsed = time.perf_counter() - start

    return {
        "name": "DefaultEventMapper",
        "iterations": iterations,
        "events_mapped": len(events),
        "elapsed_seconds": elapsed,
        "throughput_eps": len(events) / elapsed,
        "latency_us": (elapsed / len(events)) * 1_000_000 if events else 0,
    }


async def benchmark_full_pipeline(iterations: int = 1000) -> dict[str, Any]:
    """Benchmark full pipeline throughput."""
    chunks = await generate_sse_chunks(iterations)

    pipeline = Pipeline(
        decoder=SSEDecoder(),
        transforms=[JsonPathSelector("exists($.choices)")],
        event_mapper=DefaultEventMapper(),
    )

    async def byte_stream():
        for chunk in chunks:
            yield chunk

    start = time.perf_counter()
    events = []
    async for event in pipeline.process(byte_stream()):
        events.append(event)
    elapsed = time.perf_counter() - start

    return {
        "name": "FullPipeline",
        "iterations": iterations,
        "events_produced": len(events),
        "elapsed_seconds": elapsed,
        "throughput_eps": len(events) / elapsed if events else 0,
        "latency_us": (elapsed / len(events)) * 1_000_000 if events else 0,
    }


async def run_benchmarks() -> None:
    """Run all benchmarks and print results."""
    print("=" * 60)
    print("Pipeline Benchmarks")
    print("=" * 60)
    print()

    benchmarks = [
        benchmark_sse_decoder,
        benchmark_json_lines_decoder,
        benchmark_selector,
        benchmark_event_mapper,
        benchmark_full_pipeline,
    ]

    for bench in benchmarks:
        result = await bench()
        print(f"{result['name']}:")
        print(f"  Iterations: {result['iterations']}")
        print(f"  Elapsed: {result['elapsed_seconds']:.4f}s")
        if "throughput_fps" in result:
            print(f"  Throughput: {result['throughput_fps']:.0f} frames/sec")
        if "throughput_eps" in result:
            print(f"  Throughput: {result['throughput_eps']:.0f} events/sec")
        print(f"  Latency: {result['latency_us']:.2f} µs/item")
        print()


if __name__ == "__main__":
    asyncio.run(run_benchmarks())
