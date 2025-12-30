from __future__ import annotations

from namel3ss.cli.app_path import resolve_app_path
from namel3ss.cli.tools_support import extract_app_path, unknown_args_message
from namel3ss.errors.base import Namel3ssError
from namel3ss.module_loader import load_project
from namel3ss.runtime.tools.bindings import bindings_path
from namel3ss.tools.health.analyze import analyze_tool_health
from namel3ss.utils.json_tools import dumps_pretty


def run_tools_list(args: list[str], *, json_mode: bool) -> int:
    app_path, extra = extract_app_path(args)
    if extra:
        raise Namel3ssError(unknown_args_message(extra))
    app_path = resolve_app_path(app_path)
    project = load_project(app_path)
    report = analyze_tool_health(project)
    app_root = app_path.parent
    bindings_file = bindings_path(app_root)

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
        {
            "name": tool.name,
            "kind": tool.kind,
            "source": "declared",
            "status": _status_for_declared(report, tool.name),
        }
        for tool in sorted(report.declared_tools, key=lambda item: item.name)
    ]
    bindings = [
        {
            "name": name,
            "entry": binding.entry,
            "runner": binding.runner or "local",
            "sandbox": binding.sandbox,
            "enforcement": binding.enforcement,
            "source": "binding",
            "status": _status_for_binding(report, name),
        }
        for name, binding in sorted(report.bindings.items())
    ]
    payload = {
        "app_root": str(app_root),
        "bindings_path": str(bindings_file),
        "bindings_valid": report.bindings_valid,
        "bindings_error": report.bindings_error,
        "packs": packs,
        "declared": declared,
        "bindings": bindings,
    }
    if json_mode:
        print(dumps_pretty(payload))
        return 0

    print(f"App root: {payload['app_root']}")
    print(f"Bindings: {payload['bindings_path']}")
    if not report.bindings_valid and report.bindings_error:
        print("Bindings file invalid:")
        print(report.bindings_error)

    _print_section("Pack tools", packs, show_entry=False)
    _print_section("Declared tools", declared, show_entry=False)
    _print_section("Bound tools", bindings, show_entry=True)
    return 0


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


def _print_section(title: str, items: list[dict], *, show_entry: bool) -> None:
    print(f"{title}:")
    if not items:
        print("- none")
        return
    for item in items:
        status = item.get("status")
        extra = []
        if item.get("pack_id"):
            extra.append(f"pack: {item['pack_id']}")
        if show_entry and item.get("entry"):
            extra.append(f"entry: {item['entry']}")
        if show_entry and item.get("runner"):
            extra.append(f"runner: {item['runner']}")
        suffix = f" {', '.join(extra)}" if extra else ""
        print(f"- {item['name']} status {status}{suffix}")


__all__ = ["run_tools_list"]
