from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class OllamaConfig:
    host: str = "http://127.0.0.1:11434"
    timeout_seconds: int = 30


@dataclass
class OpenAIConfig:
    api_key: str | None = None
    base_url: str = "https://api.openai.com"


@dataclass
class AnthropicConfig:
    api_key: str | None = None


@dataclass
class GeminiConfig:
    api_key: str | None = None


@dataclass
class MistralConfig:
    api_key: str | None = None


@dataclass
class AppConfig:
    ollama: OllamaConfig = field(default_factory=OllamaConfig)
    openai: OpenAIConfig = field(default_factory=OpenAIConfig)
    anthropic: AnthropicConfig = field(default_factory=AnthropicConfig)
    gemini: GeminiConfig = field(default_factory=GeminiConfig)
    mistral: MistralConfig = field(default_factory=MistralConfig)


__all__ = [
    "AppConfig",
    "OllamaConfig",
    "OpenAIConfig",
    "AnthropicConfig",
    "GeminiConfig",
    "MistralConfig",
]
