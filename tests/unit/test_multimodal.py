"""扩展多模态模块单元测试。"""

from __future__ import annotations

from ai_lib_python.multimodal import (
    Modality,
    MultimodalCapabilities,
    detect_modalities,
    validate_content_modalities,
)


def _sample_config() -> dict:
    return {
        "input": {
            "vision": {
                "supported": True,
                "formats": ["jpeg", "png", "webp"],
                "encoding_methods": ["base64_inline", "url"],
                "max_file_size": "20MB",
            },
            "audio": {
                "supported": True,
                "formats": ["mp3", "wav"],
            },
            "video": None,
        },
        "output": {
            "text": True,
            "audio": {"supported": True, "formats": ["wav"]},
            "image": None,
        },
        "omni_mode": {"supported": True, "real_time_voice_chat": True},
    }


class TestMultimodalCapabilities:
    def test_from_config(self) -> None:
        caps = MultimodalCapabilities.from_config(_sample_config())
        assert caps.supports_input(Modality.TEXT)
        assert caps.supports_input(Modality.IMAGE)
        assert caps.supports_input(Modality.AUDIO)
        assert not caps.supports_input(Modality.VIDEO)
        assert caps.supports_output(Modality.AUDIO)
        assert not caps.supports_output(Modality.IMAGE)
        assert caps.supports_omni
        assert caps.supports_realtime_voice

    def test_validate_image_format(self) -> None:
        caps = MultimodalCapabilities.from_config(_sample_config())
        assert caps.validate_image_format("jpeg")
        assert caps.validate_image_format("PNG")  # case insensitive
        assert not caps.validate_image_format("bmp")

    def test_validate_audio_format(self) -> None:
        caps = MultimodalCapabilities.from_config(_sample_config())
        assert caps.validate_audio_format("mp3")
        assert not caps.validate_audio_format("flac")

    def test_validate_video_format_no_restriction(self) -> None:
        caps = MultimodalCapabilities.from_config(_sample_config())
        assert caps.validate_video_format("mp4")  # no video formats declared

    def test_empty_config(self) -> None:
        caps = MultimodalCapabilities.from_config(None)
        assert caps.supports_input(Modality.TEXT)
        assert not caps.supports_input(Modality.IMAGE)


class TestDetectModalities:
    def test_text_and_image(self) -> None:
        blocks = [
            {"type": "text", "text": "Hello"},
            {"type": "image", "source": {}},
        ]
        mods = detect_modalities(blocks)
        assert Modality.TEXT in mods
        assert Modality.IMAGE in mods
        assert Modality.AUDIO not in mods

    def test_audio(self) -> None:
        blocks = [{"type": "input_audio", "data": "..."}]
        mods = detect_modalities(blocks)
        assert Modality.AUDIO in mods

    def test_empty_defaults_to_text(self) -> None:
        assert Modality.TEXT in detect_modalities([])


class TestValidateContentModalities:
    def test_valid(self) -> None:
        caps = MultimodalCapabilities.from_config(_sample_config())
        blocks = [
            {"type": "text", "text": "Describe"},
            {"type": "image", "source": {}},
        ]
        assert validate_content_modalities(blocks, caps) == []

    def test_video_unsupported(self) -> None:
        caps = MultimodalCapabilities.from_config(_sample_config())
        blocks = [{"type": "video", "source": {}}]
        unsupported = validate_content_modalities(blocks, caps)
        assert Modality.VIDEO in unsupported
