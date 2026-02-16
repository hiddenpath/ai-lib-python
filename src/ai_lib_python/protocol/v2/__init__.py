"""V2 协议三环清单解析模块 — 支持 Ring1/Ring2/Ring3 结构的 Manifest 加载与验证。

V2 three-ring manifest parser for AI-Protocol.
Parses Ring 1 (Core Skeleton), Ring 2 (Capability Mapping), and Ring 3 (Advanced
Extensions) from provider manifests. Supports auto-promotion from V1 flat manifests.
"""

from ai_lib_python.protocol.v2.capabilities import (
    CapabilitiesV2,
    Capability,
    FeatureFlags,
    LegacyCapabilities,
)
from ai_lib_python.protocol.v2.manifest import ManifestV2

__all__ = [
    "CapabilitiesV2",
    "Capability",
    "FeatureFlags",
    "LegacyCapabilities",
    "ManifestV2",
]
