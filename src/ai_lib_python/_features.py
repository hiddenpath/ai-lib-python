"""运行时特性检测：检查可选依赖以确定可用的能力模块。

Runtime feature detection for optional extras.

Checks availability of optional dependencies to determine which
capability modules can be used.
"""
from __future__ import annotations


def _check_import(module_name: str) -> bool:
    """Check if a module is importable."""
    try:
        __import__(module_name)
        return True
    except ImportError:
        return False


# Capability feature flags
HAS_VISION: bool = _check_import("PIL")
HAS_AUDIO: bool = _check_import("soundfile")
HAS_TELEMETRY: bool = _check_import("opentelemetry")
HAS_TOKENIZER: bool = _check_import("tiktoken")
HAS_KEYRING: bool = _check_import("keyring")
HAS_WATCHDOG: bool = _check_import("watchdog")


# Map pip package names to import module names (when they differ)
_PACKAGE_TO_MODULE: dict[str, str] = {
    "pillow": "PIL",
}


def require_extra(extra_name: str, package_name: str) -> None:
    """Raise ImportError with installation hint if extra is not available.

    Args:
        extra_name: Name of the pip extra (e.g., 'vision')
        package_name: Name of the required package (e.g., 'pillow')

    Raises:
        ImportError: With installation instructions when package is not available.
    """
    module_name = _PACKAGE_TO_MODULE.get(package_name, package_name)
    if _check_import(module_name):
        return
    raise ImportError(
        f"The '{extra_name}' extra is required for this feature. "
        f"Install it with: pip install ai-lib-python[{extra_name}]"
    )
