from __future__ import annotations

from dataclasses import dataclass, field


GUARANTEE_FIELDS = (
    "no_filesystem_write",
    "no_filesystem_read",
    "no_network",
    "no_subprocess",
    "no_env_read",
    "no_env_write",
)
GUARANTEE_SOURCES = {"engine", "tool", "pack", "user", "policy"}
CAPABILITY_TO_GUARANTEE = {
    "filesystem_read": "no_filesystem_read",
    "filesystem_write": "no_filesystem_write",
    "network": "no_network",
    "subprocess": "no_subprocess",
    "env_read": "no_env_read",
    "env_write": "no_env_write",
    "secrets": "secrets_allowed",
}


@dataclass
class EffectiveGuarantees:
    no_filesystem_write: bool = False
    no_filesystem_read: bool = False
    no_network: bool = False
    no_subprocess: bool = False
    no_env_read: bool = False
    no_env_write: bool = False
    secrets_allowed: list[str] | None = None
    sources: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        payload = {
            "no_filesystem_write": self.no_filesystem_write,
            "no_filesystem_read": self.no_filesystem_read,
            "no_network": self.no_network,
            "no_subprocess": self.no_subprocess,
            "no_env_read": self.no_env_read,
            "no_env_write": self.no_env_write,
        }
        if self.secrets_allowed is not None:
            payload["secrets_allowed"] = list(self.secrets_allowed)
        return payload

    def source_for(self, key: str) -> str | None:
        return self.sources.get(key)

    def source_for_capability(self, capability: str) -> str | None:
        key = CAPABILITY_TO_GUARANTEE.get(capability)
        if not key:
            return None
        return self.sources.get(key)


@dataclass
class CapabilityContext:
    tool_name: str
    resolved_source: str
    runner: str
    protocol_version: int
    guarantees: EffectiveGuarantees
    allowed_emitted: set[str] = field(default_factory=set)

    def to_dict(self) -> dict[str, object]:
        return {
            "tool_name": self.tool_name,
            "resolved_source": self.resolved_source,
            "runner": self.runner,
            "protocol_version": self.protocol_version,
            "guarantees": self.guarantees.to_dict(),
            "sources": dict(self.guarantees.sources),
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "CapabilityContext":
        guarantees = EffectiveGuarantees(
            no_filesystem_write=bool(_get_bool(data, "guarantees", "no_filesystem_write")),
            no_filesystem_read=bool(_get_bool(data, "guarantees", "no_filesystem_read")),
            no_network=bool(_get_bool(data, "guarantees", "no_network")),
            no_subprocess=bool(_get_bool(data, "guarantees", "no_subprocess")),
            no_env_read=bool(_get_bool(data, "guarantees", "no_env_read")),
            no_env_write=bool(_get_bool(data, "guarantees", "no_env_write")),
            secrets_allowed=_get_list(data, "guarantees", "secrets_allowed"),
            sources=_get_sources(data),
        )
        return cls(
            tool_name=str(data.get("tool_name") or ""),
            resolved_source=str(data.get("resolved_source") or ""),
            runner=str(data.get("runner") or ""),
            protocol_version=int(data.get("protocol_version") or 1),
            guarantees=guarantees,
        )


@dataclass(frozen=True)
class CapabilityCheck:
    capability: str
    allowed: bool
    guarantee_source: str
    reason: str
    duration_ms: int | None = None

    def to_dict(self) -> dict[str, object]:
        payload = {
            "capability": self.capability,
            "allowed": self.allowed,
            "guarantee_source": self.guarantee_source,
            "reason": self.reason,
        }
        if self.duration_ms is not None:
            payload["duration_ms"] = self.duration_ms
        return payload


def _get_bool(data: dict[str, object], group: str, key: str) -> bool:
    block = data.get(group)
    if not isinstance(block, dict):
        return False
    value = block.get(key)
    return bool(value)


def _get_list(data: dict[str, object], group: str, key: str) -> list[str] | None:
    block = data.get(group)
    if not isinstance(block, dict):
        return None
    value = block.get(key)
    if value is None:
        return None
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    return None


def _get_sources(data: dict[str, object]) -> dict[str, str]:
    sources = data.get("sources")
    if not isinstance(sources, dict):
        return {}
    normalized: dict[str, str] = {}
    for key, value in sources.items():
        if isinstance(value, str) and value in GUARANTEE_SOURCES:
            normalized[str(key)] = value
    return normalized


__all__ = [
    "CAPABILITY_TO_GUARANTEE",
    "GUARANTEE_FIELDS",
    "GUARANTEE_SOURCES",
    "CapabilityCheck",
    "CapabilityContext",
    "EffectiveGuarantees",
]
