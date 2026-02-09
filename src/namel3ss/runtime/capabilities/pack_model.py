from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


PACK_PURITY_PURE = "pure"
PACK_PURITY_EFFECTFUL = "effectful"
PACK_REPLAY_EXECUTE = "execute"
PACK_REPLAY_VERIFY = "verify"

_ALLOWED_PURITY = {PACK_PURITY_PURE, PACK_PURITY_EFFECTFUL}
_ALLOWED_REPLAY = {PACK_REPLAY_EXECUTE, PACK_REPLAY_VERIFY}


@dataclass(frozen=True)
class CapabilityPack:
    name: str
    version: str
    provided_actions: tuple[str, ...]
    required_permissions: tuple[str, ...]
    runtime_bindings: tuple[tuple[str, str], ...]
    effect_capabilities: tuple[str, ...]
    contract_version: str
    purity: str
    replay_mode: str

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "version": self.version,
            "provided_actions": list(self.provided_actions),
            "required_permissions": list(self.required_permissions),
            "runtime_bindings": {key: value for key, value in self.runtime_bindings},
            "effect_capabilities": list(self.effect_capabilities),
            "contract_version": self.contract_version,
            "purity": self.purity,
            "replay_mode": self.replay_mode,
        }


def build_capability_pack(
    *,
    name: str,
    version: str,
    provided_actions: tuple[str, ...] | list[str],
    required_permissions: tuple[str, ...] | list[str],
    runtime_bindings: Mapping[str, str],
    effect_capabilities: tuple[str, ...] | list[str],
    contract_version: str,
    purity: str,
    replay_mode: str,
) -> CapabilityPack:
    normalized_name = _normalize_token(name)
    normalized_version = str(version or "").strip()
    if not normalized_name:
        raise ValueError("Capability pack name is required.")
    if not normalized_version:
        raise ValueError(f"Capability pack '{normalized_name}' is missing a version.")
    if purity not in _ALLOWED_PURITY:
        raise ValueError(f"Capability pack '{normalized_name}' has unsupported purity '{purity}'.")
    if replay_mode not in _ALLOWED_REPLAY:
        raise ValueError(f"Capability pack '{normalized_name}' has unsupported replay_mode '{replay_mode}'.")
    if not isinstance(contract_version, str) or not contract_version.strip():
        raise ValueError(f"Capability pack '{normalized_name}' is missing contract_version.")
    actions = _normalize_list(provided_actions)
    if not actions:
        raise ValueError(f"Capability pack '{normalized_name}' must declare provided_actions.")
    permissions = _normalize_list(required_permissions)
    bindings = _normalize_bindings(runtime_bindings)
    effects = _normalize_list(effect_capabilities)
    return CapabilityPack(
        name=normalized_name,
        version=normalized_version,
        provided_actions=actions,
        required_permissions=permissions,
        runtime_bindings=bindings,
        effect_capabilities=effects,
        contract_version=contract_version.strip(),
        purity=purity,
        replay_mode=replay_mode,
    )


def _normalize_list(values: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    deduped: dict[str, None] = {}
    for value in values:
        token = _normalize_token(value)
        if token:
            deduped[token] = None
    return tuple(sorted(deduped))


def _normalize_bindings(values: Mapping[str, str]) -> tuple[tuple[str, str], ...]:
    normalized: list[tuple[str, str]] = []
    for key, value in values.items():
        key_text = str(key or "").strip()
        value_text = str(value or "").strip()
        if key_text and value_text:
            normalized.append((key_text, value_text))
    normalized.sort(key=lambda item: item[0])
    return tuple(normalized)


def _normalize_token(value: object) -> str:
    text = str(value or "").strip().lower()
    return text


__all__ = [
    "CapabilityPack",
    "PACK_PURITY_EFFECTFUL",
    "PACK_PURITY_PURE",
    "PACK_REPLAY_EXECUTE",
    "PACK_REPLAY_VERIFY",
    "build_capability_pack",
]
