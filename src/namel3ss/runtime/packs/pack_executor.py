from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from namel3ss.errors.guidance import build_guidance_message


def normalize_pack_allowlist(values: Iterable[str] | None) -> tuple[str, ...] | None:
    if values is None:
        return None
    normalized: list[str] = []
    seen: set[str] = set()
    for item in values:
        if not isinstance(item, str):
            continue
        value = item.strip()
        if not value or value in seen:
            continue
        seen.add(value)
        normalized.append(value)
    return tuple(normalized)


@dataclass(frozen=True)
class PackAllowlistResult:
    candidates: list
    blocked_pack_ids: tuple[str, ...] | None


def apply_pack_allowlist(
    tool_name: str,
    candidates: list,
    allowlist: tuple[str, ...] | None,
    *,
    line: int | None,
    column: int | None,
) -> PackAllowlistResult:
    builtin = [item for item in candidates if getattr(item, "source", None) == "builtin_pack"]
    non_builtin = [item for item in candidates if getattr(item, "source", None) != "builtin_pack"]
    if allowlist is None:
        return PackAllowlistResult(candidates=candidates, blocked_pack_ids=None)
    allowed = list(builtin)
    allowed.extend([item for item in non_builtin if item.pack_id in allowlist])
    if allowed:
        return PackAllowlistResult(candidates=allowed, blocked_pack_ids=None)
    blocked = tuple(sorted({item.pack_id for item in non_builtin}))
    if blocked:
        return PackAllowlistResult(candidates=[], blocked_pack_ids=blocked)
    return PackAllowlistResult(candidates=[], blocked_pack_ids=None)


def pack_not_declared_message(tool_name: str, pack_ids: Iterable[str]) -> str:
    pack_ids = ", ".join(sorted({item for item in pack_ids if item}))
    return build_guidance_message(
        what=f'Tool "{tool_name}" is provided by a pack that is not declared.',
        why=f"Available packs for this tool: {pack_ids}.",
        fix="Add the pack id to the packs block or choose a different tool.",
        example='packs:\\n  "builtin.text"',
    )


__all__ = [
    "PackAllowlistResult",
    "apply_pack_allowlist",
    "normalize_pack_allowlist",
    "pack_not_declared_message",
]
