from __future__ import annotations

from pathlib import Path

from namel3ss.cli.promotion_state import load_state
from namel3ss.cli.targets import parse_target
from namel3ss.runtime.tools.bindings import bindings_path


def tool_inventory_payload(report, app_root: Path) -> dict:
    packs = []
    for name in sorted(report.pack_tools):
        for provider in report.pack_tools[name]:
            packs.append(
                {
                    "name": name,
                    "pack_id": provider.pack_id,
                    "pack_name": provider.pack_name,
                    "pack_version": provider.pack_version,
                    "verified": provider.verified,
                    "enabled": provider.enabled,
                    "runner": provider.runner,
                    "source": provider.source,
                    "status": _status_for_pack(report, name, provider),
                }
            )
    declared = [
        {"name": tool.name, "kind": tool.kind, "status": _status_for_declared(report, tool.name)}
        for tool in sorted(report.declared_tools, key=lambda item: item.name)
    ]
    bindings = [
        {
            "name": name,
            "entry": binding.entry,
            "runner": binding.runner or "local",
            "status": _status_for_binding(report, name),
        }
        for name, binding in sorted(report.bindings.items())
    ]
    invalid = sorted(
        set(
            report.invalid_bindings
            + report.invalid_runners
            + report.service_missing_urls
            + report.container_missing_images
            + report.container_missing_runtime
        )
    )
    ok_count = len([tool for tool in declared if tool["kind"] == "python" and tool["status"] == "ok"])
    summary = {
        "ok": ok_count,
        "missing": len(report.missing_bindings),
        "unused": len(report.unused_bindings),
        "collisions": len(report.collisions) + len(report.pack_collisions),
        "invalid": len(invalid),
    }
    return {
        "app_root": str(app_root),
        "bindings_path": str(bindings_path(app_root)),
        "bindings_valid": report.bindings_valid,
        "bindings_error": report.bindings_error,
        "summary": summary,
        "packs": packs,
        "pack_collisions": report.pack_collisions,
        "pack_status": [pack.__dict__ for pack in report.packs],
        "declared": declared,
        "bindings": bindings,
        "missing_bindings": report.missing_bindings,
        "unused_bindings": report.unused_bindings,
        "collisions": report.collisions,
        "invalid_bindings": report.invalid_bindings,
        "invalid_runners": report.invalid_runners,
        "service_missing_urls": report.service_missing_urls,
        "container_missing_images": report.container_missing_images,
        "container_missing_runtime": report.container_missing_runtime,
        "issues": [issue.__dict__ for issue in report.issues],
    }


def resolve_target(project_root: Path) -> str:
    state = load_state(project_root)
    active = state.get("active") or {}
    return parse_target(active.get("target")).name


def _status_for_pack(report, name: str, provider) -> str:
    if name in report.pack_collisions:
        return "collision"
    if provider.source == "builtin_pack":
        return "ok"
    if not provider.verified:
        return "unverified"
    if not provider.enabled:
        return "disabled"
    return "ok"


def _status_for_declared(report, name: str) -> str:
    if name in report.collisions:
        return "collision"
    if name in report.missing_bindings:
        return "missing binding"
    return "ok"


def _status_for_binding(report, name: str) -> str:
    if name in report.collisions:
        return "collision"
    if name in report.invalid_bindings or name in report.invalid_runners:
        return "invalid binding"
    if name in report.service_missing_urls:
        return "invalid binding"
    if name in report.container_missing_images:
        return "invalid binding"
    if name in report.container_missing_runtime:
        return "invalid binding"
    if name in report.unused_bindings:
        return "unused binding"
    return "ok"


__all__ = ["resolve_target", "tool_inventory_payload"]
