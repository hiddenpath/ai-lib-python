# ai-lib-python v0.7.5 Release Notes

**Release Date**: 2026-02-28

## Summary

This release publishes pending runtime enhancements and test hardening, including STT/TTS/Rerank client modules, safer local/mock transport defaults, and portable benchmark scaffolding.

## What's New

### New capability clients

- Added STT module: `SttClient` and typed transcription results
- Added TTS module: `TtsClient`, `AudioFormat`, and binary audio output model
- Added Rerank module: `RerankerClient` and typed rerank result model

### Test and transport robustness

- HTTP transport now works without requiring `httpx[http2]` (`h2` optional fallback)
- Proxy environment variables are ignored by default unless explicitly enabled (`AI_HTTP_TRUST_ENV=1`)
- Mock E2E checks use `trust_env=False` to avoid local proxy contamination

### Benchmark portability

- Added portable benchmark assets under `benchmarks/` with repo-local outputs
- Added benchmark workflow entrypoint as manual trigger only

## Validation

- `pytest tests/integration/test_mock_chat_e2e.py::test_chat_simple_via_mock`

