from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from namel3ss.config.model import AppConfig
from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.memory_packs.builtins import builtin_memory_packs
from namel3ss.runtime.memory_packs.format import MemoryOverrides, MemoryPack
from namel3ss.runtime.memory_packs.loader import load_memory_packs


PACK_NONE = "none"
PACK_OFF = "off"


@dataclass(frozen=True)
class MemoryPackCatalog:
    builtin: list[MemoryPack]
    local: list[MemoryPack]
    available: dict[str, MemoryPack]
    overrides: MemoryOverrides | None


@dataclass(frozen=True)
class PackSelection:
    pack_id: str | None
    mode: str
    source: str


def load_memory_pack_catalog(*, project_root: str | None, app_path: str | None) -> MemoryPackCatalog:
    load_result = load_memory_packs(project_root=project_root, app_path=app_path)
    builtin = builtin_memory_packs()
    local = list(load_result.packs)
    available = _index_available_packs(builtin, local)
    return MemoryPackCatalog(
        builtin=builtin,
        local=local,
        available=available,
        overrides=load_result.overrides,
    )


def resolve_pack_selection(config: AppConfig, *, agent_id: str | None) -> PackSelection:
    raw_default = config.memory_packs.default_pack
    default_pack = _normalize_pack_id(raw_default)
    default_none = _is_explicit_none(raw_default)
    source = "auto"
    pack_id = default_pack
    mode = "none" if default_none else ("auto" if default_pack is None else "explicit")
    if agent_id:
        override = config.memory_packs.agent_overrides.get(agent_id)
        override_pack = _normalize_pack_id(override)
        if override_pack is not None or _is_explicit_none(override):
            pack_id = override_pack
            source = "agent_override"
            mode = "none" if override_pack is None and _is_explicit_none(override) else "explicit"
    if source == "auto" and (pack_id is not None or default_none):
        source = "app_default"
    if pack_id is None and mode != "none":
        mode = "auto"
    return PackSelection(pack_id=pack_id, mode=mode, source=source)


def select_packs(
    catalog: MemoryPackCatalog,
    *,
    selection: PackSelection,
) -> list[MemoryPack]:
    if selection.mode == "none":
        return []
    if selection.pack_id is None:
        return list(catalog.local)
    pack = catalog.available.get(selection.pack_id)
    if pack is None:
        raise Namel3ssError(f"Memory pack '{selection.pack_id}' was not found.")
    return [pack]


def list_available_packs(catalog: MemoryPackCatalog) -> list[MemoryPack]:
    return sorted(catalog.available.values(), key=lambda pack: pack.pack_id)


def _index_available_packs(builtin: Iterable[MemoryPack], local: Iterable[MemoryPack]) -> dict[str, MemoryPack]:
    available: dict[str, MemoryPack] = {}
    for pack in list(builtin) + list(local):
        if pack.pack_id in available:
            raise Namel3ssError(f"Duplicate memory pack id '{pack.pack_id}'.")
        available[pack.pack_id] = pack
    return available


def _normalize_pack_id(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    lowered = text.lower()
    if lowered in {PACK_NONE, PACK_OFF}:
        return None
    return text


def _is_explicit_none(value: object) -> bool:
    if value is None:
        return False
    text = str(value).strip().lower()
    return text in {PACK_NONE, PACK_OFF}


__all__ = [
    "MemoryPackCatalog",
    "PACK_NONE",
    "PackSelection",
    "list_available_packs",
    "load_memory_pack_catalog",
    "resolve_pack_selection",
    "select_packs",
]
