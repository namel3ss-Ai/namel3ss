from __future__ import annotations

from typing import Dict, List

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.module_loader.types import ModuleExports


KIND_LABELS = {
    "record": "record",
    "flow": "flow",
    "page": "page",
    "ai": "AI profile",
    "agent": "agent",
    "tool": "tool",
    "function": "function",
    "ui_pack": "ui pack",
}


def qualify(module_name: str | None, name: str) -> str:
    return f"{module_name}.{name}" if module_name else name


def resolve_name(
    raw: str,
    *,
    kind: str,
    module_name: str | None,
    alias_map: Dict[str, str],
    local_defs: Dict[str, set[str]],
    exports_map: Dict[str, ModuleExports],
    context_label: str,
    line: int | None = None,
    column: int | None = None,
) -> str:
    prefix, rest = _split_alias(raw)
    if prefix:
        if prefix not in alias_map:
            if raw in local_defs.get(kind, set()):
                return qualify(module_name, raw)
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Unknown module alias '{prefix}'.",
                    why=f"{context_label} does not define alias '{prefix}'.",
                    fix=f'Add `use "<module>" as {prefix}` or correct the alias.',
                    example=f'use "inventory" as {prefix}',
                ),
                line=line,
                column=column,
            )
        target_module = alias_map[prefix]
        if not exports_map.get(target_module, ModuleExports()).has(kind, rest):
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Module '{target_module}' does not export {KIND_LABELS[kind]} '{rest}'.",
                    why="Only symbols listed in capsule.ai are visible outside a module.",
                    fix="Export the symbol in modules/<name>/capsule.ai or reference an exported symbol.",
                    example=f'exports:\n  {kind} "{rest}"',
                ),
                line=line,
                column=column,
                details={"module": target_module, "kind": kind, "name": rest},
            )
        return qualify(target_module, rest)
    if raw in local_defs.get(kind, set()):
        return qualify(module_name, raw)
    if _is_exported_elsewhere(raw, kind, exports_map):
        suggestions = _exporting_modules(raw, kind, exports_map)
        hint = _alias_hint(suggestions, alias_map, raw)
        raise Namel3ssError(
            build_guidance_message(
                what=f"Unqualified reference to {KIND_LABELS[kind]} '{raw}'.",
                why="Cross-module references must use an explicit alias.",
                fix=hint,
                example=_alias_example(suggestions, raw),
            ),
            line=line,
            column=column,
        )
    raise Namel3ssError(
        build_guidance_message(
            what=f"Unknown {KIND_LABELS[kind]} '{raw}'.",
            why=f"{context_label} does not define this {KIND_LABELS[kind]}.",
            fix=f"Define the {KIND_LABELS[kind]} locally or import it with a module alias.",
            example='use "inventory" as inv',
        ),
        line=line,
        column=column,
    )


def _split_alias(raw: str) -> tuple[str | None, str]:
    if "." not in raw:
        return None, raw
    prefix, rest = raw.split(".", 1)
    return prefix, rest


def _is_exported_elsewhere(raw: str, kind: str, exports_map: Dict[str, ModuleExports]) -> bool:
    return any(exports.has(kind, raw) for exports in exports_map.values())


def _exporting_modules(raw: str, kind: str, exports_map: Dict[str, ModuleExports]) -> List[str]:
    return sorted(module for module, exports in exports_map.items() if exports.has(kind, raw))


def _alias_hint(modules: List[str], alias_map: Dict[str, str], raw: str | None = None) -> str:
    if not modules:
        return "Add a module import and qualify the reference."
    module_name = modules[0]
    alias = _alias_for_module(module_name, alias_map)
    if alias:
        suffix = raw or "<name>"
        return f"Use `{alias}.{suffix}` with the existing alias."
    suggested = module_name[:3]
    return f'Add `use "{module_name}" as {suggested}` and qualify the reference.'


def _alias_example(modules: List[str], raw: str) -> str:
    if not modules:
        return f'use "inventory" as inv\n...\ninv.{raw}'
    module = modules[0]
    alias = module[:3]
    return f'use "{module}" as {alias}\n...\n{alias}.{raw}'


def _alias_for_module(module_name: str, alias_map: Dict[str, str]) -> str | None:
    for alias, mod in alias_map.items():
        if mod == module_name:
            return alias
    return None


__all__ = ["KIND_LABELS", "qualify", "resolve_name"]
