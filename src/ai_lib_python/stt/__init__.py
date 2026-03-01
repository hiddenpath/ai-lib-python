"""STT 模块：封装语音转文本能力。

STT (Speech-to-Text) module.

Provides transcription of audio to text via provider APIs (e.g. OpenAI Whisper).
"""

from ai_lib_python.stt.client import (
    SttClient,
    SttClientBuilder,
    SttOptions,
    Transcription,
    TranscriptionSegment,
)

__all__ = [
    "SttClient",
    "SttClientBuilder",
    "SttOptions",
    "Transcription",
    "TranscriptionSegment",
]
