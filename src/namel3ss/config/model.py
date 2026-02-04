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
class AnswerConfig:
    provider: str = "mock"
    model: str = "mock-model"


@dataclass
class EmbeddingConfig:
    provider: str = "hash"
    model: str = "hash"
    version: str = "v1"
    dims: int = 64
    precision: int = 6
    candidate_limit: int = 50


@dataclass
class PersistenceConfig:
    target: str = "memory"
    db_path: str = ".namel3ss/data.db"
    database_url: str | None = None
    edge_kv_url: str | None = None
    replica_urls: list[str] = field(default_factory=list)


@dataclass
class IdentityConfig:
    defaults: dict[str, object] = field(default_factory=dict)


@dataclass
class AuthenticationConfig:
    signing_key: str | None = None
    allow_identity: bool = False
    username: str | None = None
    password: str | None = None
    identity: dict[str, object] = field(default_factory=dict)


@dataclass
class PythonToolsConfig:
    timeout_seconds: int = 10
    service_url: str | None = None
    service_handshake_required: bool | None = None


@dataclass
class ForeignConfig:
    strict: bool = False
    allow: bool = False


@dataclass
class ToolPacksConfig:
    enabled_packs: list[str] = field(default_factory=list)
    disabled_packs: list[str] = field(default_factory=list)
    pinned_tools: dict[str, str] = field(default_factory=dict)


@dataclass
class MemoryPacksConfig:
    default_pack: str | None = None
    agent_overrides: dict[str, str] = field(default_factory=dict)


@dataclass
class RegistrySourceConfig:
    id: str
    kind: str
    path: str | None = None
    url: str | None = None


@dataclass
class RegistriesConfig:
    sources: list[RegistrySourceConfig] = field(default_factory=list)
    default: list[str] = field(default_factory=list)


@dataclass
class AppConfig:
    ollama: OllamaConfig = field(default_factory=OllamaConfig)
    openai: OpenAIConfig = field(default_factory=OpenAIConfig)
    anthropic: AnthropicConfig = field(default_factory=AnthropicConfig)
    gemini: GeminiConfig = field(default_factory=GeminiConfig)
    mistral: MistralConfig = field(default_factory=MistralConfig)
    answer: AnswerConfig = field(default_factory=AnswerConfig)
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    persistence: PersistenceConfig = field(default_factory=PersistenceConfig)
    identity: IdentityConfig = field(default_factory=IdentityConfig)
    authentication: AuthenticationConfig = field(default_factory=AuthenticationConfig)
    python_tools: PythonToolsConfig = field(default_factory=PythonToolsConfig)
    foreign: ForeignConfig = field(default_factory=ForeignConfig)
    tool_packs: ToolPacksConfig = field(default_factory=ToolPacksConfig)
    memory_packs: MemoryPacksConfig = field(default_factory=MemoryPacksConfig)
    registries: RegistriesConfig = field(default_factory=RegistriesConfig)
    capability_overrides: dict[str, dict[str, object]] = field(default_factory=dict)


__all__ = [
    "AppConfig",
    "OllamaConfig",
    "OpenAIConfig",
    "AnthropicConfig",
    "GeminiConfig",
    "MistralConfig",
    "AnswerConfig",
    "EmbeddingConfig",
    "PersistenceConfig",
    "IdentityConfig",
    "AuthenticationConfig",
    "PythonToolsConfig",
    "ForeignConfig",
    "ToolPacksConfig",
    "MemoryPacksConfig",
    "RegistrySourceConfig",
    "RegistriesConfig",
]
