from __future__ import annotations

from typing import Iterable, List

from namel3ss.runtime.modules.format import ModuleLoadResult, ModuleOverride, MODULE_CATEGORIES, SourceInfo


def render_module_loaded(module: ModuleLoadResult) -> List[str]:
    lines: List[str] = [
        f"module {module.alias} loaded",
        f"path {module.module_id}",
    ]
    any_items = False
    for category in MODULE_CATEGORIES:
        names = module.provided.get(category) or []
        if not names:
            continue
        any_items = True
        lines.append(f"provides {category}: {', '.join(names)}")
    if not any_items:
        lines.append("provides nothing")
    return lines


def render_module_merged(modules: Iterable[ModuleLoadResult]) -> List[str]:
    aliases = [module.alias for module in modules]
    if not aliases:
        return ["no modules merged"]
    return [f"merge order: {', '.join(aliases)}"]


def render_module_overrides(overrides: Iterable[ModuleOverride]) -> List[str]:
    lines: List[str] = []
    for entry in overrides:
        prev = _source_label(entry.previous)
        current = _source_label(entry.current)
        lines.append(f"{entry.kind} {entry.name} overridden by {current}, was from {prev}")
    if not lines:
        lines.append("no overrides")
    return lines


def _source_label(source: SourceInfo) -> str:
    if source.origin == "main":
        return "main file"
    if source.origin == "module":
        alias = source.module_alias or "module"
        return f"module {alias}"
    return source.origin


__all__ = ["render_module_loaded", "render_module_merged", "render_module_overrides"]
