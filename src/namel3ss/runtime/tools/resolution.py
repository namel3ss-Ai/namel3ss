from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.config.model import AppConfig
from namel3ss.runtime.packs.pack_executor import (
    apply_pack_allowlist,
    normalize_pack_allowlist,
    pack_not_declared_message,
)
from namel3ss.runtime.packs.permission_enforcer import evaluate_pack_permission
from namel3ss.runtime.packs.policy import load_pack_policy
from namel3ss.runtime.packs.registry import load_pack_registry
from namel3ss.runtime.tools.bindings import bindings_path, load_tool_bindings
from namel3ss.runtime.tools.bindings_yaml import ToolBinding
from namel3ss.runtime.tools.default_bindings import default_tool_bindings, default_tool_paths
from namel3ss.utils.slugify import slugify_tool_name


@dataclass(frozen=True)
class ResolvedToolBinding:
    binding: ToolBinding
    source: str
    pack_id: str | None = None
    pack_name: str | None = None
    pack_version: str | None = None
    pack_paths: list[Path] | None = None


def resolve_tool_binding(
    app_root: Path,
    tool_name: str,
    config: AppConfig,
    *,
    tool_kind: str | None = None,
    line: int | None,
    column: int | None,
    allowed_packs: list[str] | tuple[str, ...] | None = None,
) -> ResolvedToolBinding:
    bindings = None
    binding_error: Namel3ssError | None = None
    try:
        bindings = load_tool_bindings(app_root)
    except Namel3ssError as err:
        binding_error = err
    allowlist = normalize_pack_allowlist(allowed_packs)
    registry = load_pack_registry(app_root, config)
    policy = load_pack_policy(app_root)
    pack_candidates = registry.tools.get(tool_name, [])
    allowlist_result = apply_pack_allowlist(tool_name, pack_candidates, allowlist, line=line, column=column)
    pack_candidates = allowlist_result.candidates
    blocked_pack_ids = allowlist_result.blocked_pack_ids
    pinned = config.tool_packs.pinned_tools.get(tool_name) if config.tool_packs else None
    if pinned is None and len(pack_candidates) > 1:
        raise Namel3ssError(
            _pack_collision_message(tool_name, pack_candidates),
            line=line,
            column=column,
            details={"tool_reason": "pack_collision"},
        )
    active_candidates = []
    for item in pack_candidates:
        if item.source == "builtin_pack":
            active_candidates.append(item)
            continue
        if not item.enabled:
            continue
        if item.verified:
            active_candidates.append(item)
            continue
        pack_record = registry.packs.get(item.pack_id) if item.pack_id else None
        if pack_record:
            decision = evaluate_pack_permission(pack_record, app_root=app_root, policy=policy)
            if decision.allowed:
                active_candidates.append(item)
    if active_candidates:
        if bindings is not None and tool_name in bindings:
            raise Namel3ssError(
                _collision_message(tool_name),
                line=line,
                column=column,
                details={"tool_reason": "pack_collision"},
            )
        selected = _select_pack_tool(active_candidates, config, tool_name, line, column)
        return ResolvedToolBinding(
            binding=selected.binding,
            source=selected.source,
            pack_id=selected.pack_id,
            pack_name=selected.pack_name,
            pack_version=selected.pack_version,
            pack_paths=_pack_paths(selected.pack_root),
        )
    if bindings is not None:
        binding = bindings.get(tool_name)
        if binding:
            return ResolvedToolBinding(binding=binding, source="binding")
    if binding_error is not None:
        raise binding_error
    if blocked_pack_ids and pinned is None and len(blocked_pack_ids) > 1:
        raise Namel3ssError(
            _pack_collision_message_for_ids(tool_name, blocked_pack_ids),
            line=line,
            column=column,
            details={"tool_reason": "pack_collision", "pack_ids": list(blocked_pack_ids)},
        )
    if blocked_pack_ids:
        raise Namel3ssError(
            pack_not_declared_message(tool_name, blocked_pack_ids),
            line=line,
            column=column,
            details={"tool_reason": "pack_not_declared", "pack_ids": list(blocked_pack_ids)},
        )
    if pack_candidates:
        raise Namel3ssError(
            _pack_unavailable_message(tool_name, pack_candidates),
            line=line,
            column=column,
            details={"tool_reason": "pack_unavailable_or_unverified"},
        )
    if not bindings_path(app_root).exists() and os.getenv("N3_EXECUTABLE_SPEC") != "1":
        if tool_kind in {None, "python"}:
            defaults = default_tool_bindings()
            default_binding = defaults.get(tool_name)
            if default_binding:
                return ResolvedToolBinding(
                    binding=default_binding,
                    source="binding",
                    pack_paths=default_tool_paths(),
                )
            slug = slugify_tool_name(tool_name)
            tools_dir = app_root / "tools"
            py_file = tools_dir / f"{slug}.py"
            pkg_init = tools_dir / slug / "__init__.py"
            if py_file.exists() or pkg_init.exists():
                local_binding = ToolBinding(kind="python", entry=f"tools.{slug}:run")
                return ResolvedToolBinding(
                    binding=local_binding,
                    source="binding",
                    pack_paths=[app_root],
                )
        if tool_kind == "node":
            slug = slugify_tool_name(tool_name)
            tools_dir = app_root / "tools"
            extensions = [".js", ".cjs", ".mjs", ".ts"]
            if any((tools_dir / f"{slug}{ext}").exists() for ext in extensions):
                local_binding = ToolBinding(kind="node", entry=f"tools.{slug}:run", runner="node")
                return ResolvedToolBinding(
                    binding=local_binding,
                    source="binding",
                    pack_paths=[app_root],
                )
    slug = slugify_tool_name(tool_name)
    kind_label = tool_kind or "python"
    raise Namel3ssError(
        build_guidance_message(
            what=f'Tool "{tool_name}" is not bound to a {kind_label} entry.',
            why="Tool declarations no longer include module paths; bindings live in .namel3ss/tools.yaml.",
            fix=(
                "Run `n3 tools status` then "
                f'`n3 tools bind "{tool_name}" --entry "tools.{slug}:run"`.'
            ),
            example=_bindings_example(tool_name, tool_kind),
        ),
        line=line,
        column=column,
        details={"tool_reason": "missing_binding"},
    )


def _collision_message(tool_name: str) -> str:
    return build_guidance_message(
        what=f'Tool "{tool_name}" collides with a tool pack.',
        why="Pack tools have priority and custom bindings with the same name are ignored.",
        fix="Rename the tool or disable the pack before binding.",
        example=f'n3 tools unbind "{tool_name}"',
    )


def _bindings_example(tool_name: str, tool_kind: str | None) -> str:
    kind = tool_kind or "python"
    return (
        "tools:\n"
        f'  "{tool_name}":\n'
        f'    kind: "{kind}"\n'
        '    entry: "tools.my_tool:run"'
    )


def _pack_unavailable_message(tool_name: str, candidates: list) -> str:
    pack_ids = ", ".join(sorted({item.pack_id for item in candidates}))
    sources = {item.source for item in candidates if getattr(item, "source", None)}
    if sources == {"installed_pack"}:
        pack_label = "installed pack"
    elif sources == {"local_pack"}:
        pack_label = "local pack"
    elif sources == {"builtin_pack"}:
        pack_label = "built-in pack"
    else:
        pack_label = "pack"
    article = "an" if pack_label[:1].lower() in {"a", "e", "i", "o", "u"} else "a"
    return build_guidance_message(
        what=f'Tool "{tool_name}" is provided by {article} {pack_label} but is unavailable.',
        why=f"Pack tool is not verified or enabled (packs: {pack_ids}).",
        fix=(
            f'Run `n3 packs verify {pack_ids.split(",")[0]}` then '
            f'`n3 packs enable {pack_ids.split(",")[0]}`.'
        ),
        example="n3 packs status",
    )


def _select_pack_tool(candidates: list, config: AppConfig, tool_name: str, line: int | None, column: int | None):
    pinned = config.tool_packs.pinned_tools.get(tool_name) if config.tool_packs else None
    if pinned:
        for item in candidates:
            if item.pack_id == pinned:
                return item
        raise Namel3ssError(
            _pack_pin_missing_message(tool_name, pinned),
            line=line,
            column=column,
            details={"tool_reason": "pack_pin_missing"},
        )
    if len(candidates) > 1:
        raise Namel3ssError(
            _pack_collision_message(tool_name, candidates),
            line=line,
            column=column,
            details={"tool_reason": "pack_collision"},
        )
    return candidates[0]


def _pack_collision_message(tool_name: str, candidates: list) -> str:
    packs = ", ".join(sorted({item.pack_id for item in candidates}))
    return build_guidance_message(
        what=f'Tool "{tool_name}" is provided by multiple packs.',
        why=f"Conflicting packs: {packs}.",
        fix="Disable one pack or pin the tool to a specific pack.",
        example=f'pinned_tools = {{ "{tool_name}" = "{candidates[0].pack_id}" }}',
    )


def _pack_collision_message_for_ids(tool_name: str, pack_ids: list[str] | tuple[str, ...]) -> str:
    packs = ", ".join(sorted({item for item in pack_ids if item}))
    example_pack = sorted({item for item in pack_ids if item})[0] if packs else "pack.id"
    return build_guidance_message(
        what=f'Tool "{tool_name}" is provided by multiple packs.',
        why=f"Conflicting packs: {packs}.",
        fix="Disable one pack or pin the tool to a specific pack.",
        example=f'pinned_tools = {{ "{tool_name}" = "{example_pack}" }}',
    )


def _pack_pin_missing_message(tool_name: str, pack_id: str) -> str:
    return build_guidance_message(
        what=f'Tool "{tool_name}" is pinned to "{pack_id}" but the pack is unavailable.',
        why="The pinned pack is not installed or not enabled.",
        fix="Install/enable the pack or update the pin.",
        example=f'pinned_tools = {{ "{tool_name}" = "{pack_id}" }}',
    )


def _pack_paths(pack_root: Path | None) -> list[Path] | None:
    if pack_root is None:
        return None
    paths: list[Path] = []
    tools_dir = pack_root / "tools"
    src_dir = pack_root / "src"
    paths.append(pack_root)
    if src_dir.exists():
        paths.append(src_dir)
    if tools_dir.exists():
        paths.append(tools_dir)
    return paths or None


__all__ = ["ResolvedToolBinding", "resolve_tool_binding"]
