from __future__ import annotations

from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.packs.layout import pack_manifest_path
from namel3ss.tools.health.model import PackSummary, PackToolSummary, ToolIssue


def collect_pack_inventory(pack_registry, config) -> tuple[dict[str, list[PackToolSummary]], list[PackSummary], list[ToolIssue], list[str]]:
    pack_tools: dict[str, list[PackToolSummary]] = {}
    pack_summaries: list[PackSummary] = []
    issues: list[ToolIssue] = []
    for pack in pack_registry.packs.values():
        pack_summaries.append(
            PackSummary(
                pack_id=pack.pack_id,
                name=pack.name,
                version=pack.version,
                description=pack.description,
                author=pack.author,
                license=pack.license,
                tools=pack.tools,
                source=pack.source,
                verified=pack.verified,
                enabled=pack.enabled,
                errors=pack.errors,
            )
        )
        if pack.errors:
            issues.append(
                ToolIssue(
                    code="packs.invalid_pack",
                    message=" ".join(pack.errors),
                    severity="error",
                    tool_name=None,
                    file=str(pack_manifest_path(pack.pack_root)) if pack.pack_root else None,
                )
            )
        if pack.source == "installed_pack" and not pack.verified:
            severity = "error" if pack.enabled else "warning"
            code = "packs.unverified_enabled" if pack.enabled else "packs.unverified"
            issues.append(
                ToolIssue(
                    code=code,
                    message=_pack_unverified_message(pack.pack_id, pack.enabled),
                    severity=severity,
                    tool_name=None,
                    file=str(pack_manifest_path(pack.pack_root)) if pack.pack_root else None,
                )
            )
    for tool_name, providers in pack_registry.tools.items():
        pack_tools[tool_name] = [
            PackToolSummary(
                tool_name=tool_name,
                pack_id=item.pack_id,
                pack_name=item.pack_name,
                pack_version=item.pack_version,
                source=item.source,
                verified=item.verified,
                enabled=item.enabled,
                runner=item.binding.runner or "local",
            )
            for item in providers
        ]
    pack_collisions = _pack_collisions(pack_registry, config)
    for tool_name in pack_collisions:
        issues.append(
            ToolIssue(
                code="packs.collision",
                message=_pack_collision_message(tool_name, pack_registry),
                severity="error",
                tool_name=tool_name,
            )
        )
    pinned = config.tool_packs.pinned_tools if config.tool_packs else {}
    for tool_name, pack_id in pinned.items():
        if pack_id not in pack_registry.packs:
            issues.append(
                ToolIssue(
                    code="packs.invalid_pin",
                    message=_pack_pin_invalid_message(tool_name, pack_id),
                    severity="error",
                    tool_name=tool_name,
                )
            )
    return pack_tools, pack_summaries, issues, pack_collisions


def active_pack_tool_names(pack_tools: dict[str, list[PackToolSummary]]) -> set[str]:
    active = set()
    for name, providers in pack_tools.items():
        for provider in providers:
            if provider.source == "builtin_pack" or (provider.verified and provider.enabled):
                active.add(name)
                break
    return active


def _pack_collisions(pack_registry, config) -> list[str]:
    collisions: list[str] = []
    pinned = config.tool_packs.pinned_tools if config.tool_packs else {}
    for tool_name, providers in pack_registry.collisions.items():
        active = [item for item in providers if item.source == "builtin_pack" or (item.verified and item.enabled)]
        if len(active) <= 1:
            continue
        pin = pinned.get(tool_name)
        if pin and any(item.pack_id == pin for item in active):
            continue
        collisions.append(tool_name)
    return sorted(set(collisions))


def _pack_unverified_message(pack_id: str, enabled: bool) -> str:
    if enabled:
        return build_guidance_message(
            what=f'Pack "{pack_id}" is enabled but unverified.',
            why="Unverified packs cannot be executed by default.",
            fix="Verify the pack before enabling it.",
            example=f"n3 packs verify {pack_id}",
        )
    return build_guidance_message(
        what=f'Pack "{pack_id}" is unverified.',
        why="Unverified packs remain inactive until verified and enabled.",
        fix="Verify the pack, then enable it.",
        example=f"n3 packs verify {pack_id}",
    )


def _pack_collision_message(tool_name: str, pack_registry) -> str:
    pack_ids = ", ".join(sorted({item.pack_id for item in pack_registry.collisions.get(tool_name, [])}))
    return build_guidance_message(
        what=f'Tool "{tool_name}" is provided by multiple packs.',
        why=f"Conflicting packs: {pack_ids}.",
        fix="Disable one pack or pin the tool to a specific pack.",
        example=f'pinned_tools = {{ "{tool_name}" = "{pack_ids.split(",")[0]}" }}',
    )


def _pack_pin_invalid_message(tool_name: str, pack_id: str) -> str:
    return build_guidance_message(
        what=f'Tool "{tool_name}" is pinned to missing pack "{pack_id}".',
        why="Pinned pack id was not found among installed packs.",
        fix="Install the pack or update the pin.",
        example=f'pinned_tools = {{ "{tool_name}" = "{pack_id}" }}',
    )


__all__ = ["active_pack_tool_names", "collect_pack_inventory"]
