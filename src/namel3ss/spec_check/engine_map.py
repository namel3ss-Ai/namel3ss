from __future__ import annotations

ENGINE_SUPPORTED_SPECS: tuple[str, ...] = (
    "1.0",
)

SPEC_CAPABILITIES: dict[str, frozenset[str]] = {
    "1.0": frozenset(
        {
            "records_v1",
            "pages_v1",
            "ai_v1",
            "tools_v1",
            "http",
            "files",
            "jobs",
            "scheduling",
            "uploads",
            "secrets",
            "embedding",
            "vision",
            "speech",
            "huggingface",
            "local_runner",
            "vision_gen",
            "third_party_apis",
            "training",
            "streaming",
            "performance",
            "performance_scalability",
            "agents_v1",
            "identity_v1",
            "theme_v1",
        }
    ),
}

__all__ = ["ENGINE_SUPPORTED_SPECS", "SPEC_CAPABILITIES"]
