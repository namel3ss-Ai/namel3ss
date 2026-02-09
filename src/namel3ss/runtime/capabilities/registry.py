from __future__ import annotations

from collections.abc import Iterable

from namel3ss.lang.capabilities import normalize_builtin_capability
from namel3ss.runtime.capabilities.email_pack import email_capability_pack
from namel3ss.runtime.capabilities.http_pack import http_capability_pack
from namel3ss.runtime.capabilities.pack_model import CapabilityPack
from namel3ss.runtime.capabilities.sql_pack import sql_capability_pack


CAPABILITY_PACK_REGISTRY_VERSION = "capability-pack-registry@1"


def list_capability_packs() -> tuple[CapabilityPack, ...]:
    packs = (email_capability_pack(), http_capability_pack(), sql_capability_pack())
    return tuple(sorted(packs, key=lambda pack: pack.name))


def get_capability_pack(name: str) -> CapabilityPack | None:
    normalized = _normalize_name(name)
    if not normalized:
        return None
    for pack in list_capability_packs():
        if pack.name == normalized:
            return pack
    return None


def capability_pack_names() -> tuple[str, ...]:
    return tuple(pack.name for pack in list_capability_packs())


def resolve_enabled_capability_packs(capability_tokens: Iterable[str] | None) -> tuple[CapabilityPack, ...]:
    permissions = set(normalize_capability_permissions(capability_tokens))
    enabled: list[CapabilityPack] = []
    for pack in list_capability_packs():
        required = set(pack.required_permissions)
        if required and not required.issubset(permissions):
            continue
        enabled.append(pack)
    enabled.sort(key=lambda pack: pack.name)
    return tuple(enabled)


def normalize_capability_permissions(capability_tokens: Iterable[str] | None) -> tuple[str, ...]:
    deduped: dict[str, None] = {}
    for value in capability_tokens or ():
        token = normalize_builtin_capability(value if isinstance(value, str) else None)
        if token:
            deduped[token] = None
    return tuple(sorted(deduped))


def capability_versions_map(packs: Iterable[CapabilityPack]) -> dict[str, str]:
    versions: dict[str, str] = {}
    for pack in sorted(packs, key=lambda item: item.name):
        versions[pack.name] = pack.version
    return versions


def capability_payload_list(packs: Iterable[CapabilityPack]) -> list[dict[str, object]]:
    return [pack.to_dict() for pack in sorted(packs, key=lambda item: item.name)]


def _normalize_name(value: object) -> str:
    text = str(value or "").strip().lower()
    return text


__all__ = [
    "CAPABILITY_PACK_REGISTRY_VERSION",
    "capability_pack_names",
    "capability_payload_list",
    "capability_versions_map",
    "get_capability_pack",
    "list_capability_packs",
    "normalize_capability_permissions",
    "resolve_enabled_capability_packs",
]
