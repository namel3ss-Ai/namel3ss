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
            "agents_v1",
            "identity_v1",
            "theme_v1",
        }
    ),
}

__all__ = ["ENGINE_SUPPORTED_SPECS", "SPEC_CAPABILITIES"]
