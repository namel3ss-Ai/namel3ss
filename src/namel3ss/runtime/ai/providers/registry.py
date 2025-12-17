from __future__ import annotations

from namel3ss.config import load_config
from namel3ss.config.model import AppConfig
from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.ai.provider import AIProvider
from namel3ss.runtime.ai.providers.mock import MockProvider
from namel3ss.runtime.ai.providers.ollama import OllamaProvider
from namel3ss.runtime.ai.providers.openai import OpenAIProvider
from namel3ss.runtime.ai.providers.anthropic import AnthropicProvider
from namel3ss.runtime.ai.providers.gemini import GeminiProvider
from namel3ss.runtime.ai.providers.mistral import MistralProvider


_FACTORIES = {
    "mock": lambda config: MockProvider(),
    "ollama": lambda config: OllamaProvider(
        host=config.ollama.host,
        timeout_seconds=config.ollama.timeout_seconds,
    ),
    "openai": lambda config: OpenAIProvider.from_config(config.openai),
    "anthropic": lambda config: AnthropicProvider.from_config(config.anthropic),
    "gemini": lambda config: GeminiProvider.from_config(config.gemini),
    "mistral": lambda config: MistralProvider.from_config(config.mistral),
}


def is_supported_provider(name: str) -> bool:
    return name.lower() in _FACTORIES


def get_provider(name: str, config: AppConfig | None = None) -> AIProvider:
    normalized = name.lower()
    if normalized not in _FACTORIES:
        available = ", ".join(sorted(_FACTORIES))
        raise Namel3ssError(f"Unknown AI provider '{name}'. Available: {available}")
    cfg = config or load_config()
    return _FACTORIES[normalized](cfg)
