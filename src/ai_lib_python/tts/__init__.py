"""TTS 模块：封装文本转语音能力。

TTS (Text-to-Speech) module.

Provides synthesis of text to audio via provider APIs (e.g. OpenAI TTS).
"""

from ai_lib_python.tts.client import (
    AudioFormat,
    AudioOutput,
    TtsClient,
    TtsClientBuilder,
    TtsOptions,
)

__all__ = [
    "AudioFormat",
    "AudioOutput",
    "TtsClient",
    "TtsClientBuilder",
    "TtsOptions",
]
