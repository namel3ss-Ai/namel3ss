from __future__ import annotations

from dataclasses import dataclass

from namel3ss.errors.base import Namel3ssError


@dataclass(frozen=True)
class ProviderCapabilities:
    supports_tools: bool
    supports_json_mode: bool
    supports_streaming: bool
    supports_system_prompt: bool
    supports_vision: bool = False
    notes: str | None = None
    max_context_tokens: int | None = None


_CAPABILITIES: dict[str, ProviderCapabilities] = {
    "mock": ProviderCapabilities(
        supports_tools=True,
        supports_json_mode=False,
        supports_streaming=False,
        supports_system_prompt=True,
        notes="Test double that can emit tool calls via a seeded sequence.",
    ),
    "ollama": ProviderCapabilities(
        supports_tools=False,
        supports_json_mode=False,
        supports_streaming=False,
        supports_system_prompt=True,
        notes="Text chat endpoint only; no tool calling or JSON mode wiring yet.",
    ),
    "openai": ProviderCapabilities(
        supports_tools=True,
        supports_json_mode=False,
        supports_streaming=False,
        supports_system_prompt=True,
        notes="Chat completions path with single tool call support; JSON mode not wired.",
    ),
    "anthropic": ProviderCapabilities(
        supports_tools=True,
        supports_json_mode=False,
        supports_streaming=False,
        supports_system_prompt=True,
        notes="Messages API with single tool call support; JSON mode not wired.",
    ),
    "gemini": ProviderCapabilities(
        supports_tools=True,
        supports_json_mode=False,
        supports_streaming=False,
        supports_system_prompt=True,
        notes="Text path with single tool call support; system prompt appended to user input.",
    ),
    "mistral": ProviderCapabilities(
        supports_tools=True,
        supports_json_mode=False,
        supports_streaming=False,
        supports_system_prompt=True,
        notes="Chat completions with single tool call support; JSON mode not wired.",
    ),
}


def get_provider_capabilities(provider_name: str) -> ProviderCapabilities:
    key = provider_name.lower()
    if key not in _CAPABILITIES:
        available = ", ".join(sorted(_CAPABILITIES))
        raise Namel3ssError(f"Unknown AI provider '{provider_name}'. Available: {available}")
    return _CAPABILITIES[key]


def list_known_providers() -> tuple[str, ...]:
    return tuple(sorted(_CAPABILITIES))


__all__ = [
    "ProviderCapabilities",
    "get_provider_capabilities",
    "list_known_providers",
]
