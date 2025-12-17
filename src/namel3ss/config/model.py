from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class OllamaConfig:
    host: str = "http://127.0.0.1:11434"
    timeout_seconds: int = 30


@dataclass
class AppConfig:
    ollama: OllamaConfig = field(default_factory=OllamaConfig)


__all__ = ["AppConfig", "OllamaConfig"]
