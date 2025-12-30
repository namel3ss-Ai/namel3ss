from __future__ import annotations

from namel3ss.cli.app_path import resolve_app_path
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.module_loader import load_project
from namel3ss.tools.health.analyze import analyze_tool_health
from namel3ss.utils.json_tools import dumps_pretty


def run_tools_search(args: list[str], *, json_mode: bool) -> int:
    if not args:
        raise Namel3ssError(_missing_query_message())
    query = args[0]
    app_path = None
    extra = args[1:]
    if extra and extra[0].endswith(".ai"):
        app_path = extra[0]
        extra = extra[1:]
    if extra:
        raise Namel3ssError(_unknown_args_message(extra))

    app_path = resolve_app_path(app_path)
    project = load_project(app_path)
    report = analyze_tool_health(project)
    needle = query.lower()

    results: list[dict] = []
    for name in sorted(report.pack_tools):
        if needle not in name.lower():
            continue
        for provider in report.pack_tools[name]:
            results.append(
                {
                    "name": name,
                    "source": provider.source,
                    "status": _status_for_pack(report, name, provider),
                    "pack_id": provider.pack_id,
                    "pack_name": provider.pack_name,
                    "pack_version": provider.pack_version,
                    "verified": provider.verified,
                    "enabled": provider.enabled,
                    "usage": _usage_for_tool(name),
                    "fix": _pack_fix(provider),
                }
            )
    for tool in sorted(report.declared_tools, key=lambda item: item.name):
        if needle in tool.name.lower():
            results.append(
                {
                    "name": tool.name,
                    "source": "declared",
                    "status": _status_for_declared(report, tool.name),
                    "usage": _usage_for_tool(tool.name),
                }
            )
    for name, binding in sorted(report.bindings.items()):
        if needle in name.lower():
            results.append(
                {
                    "name": name,
                    "source": "binding",
                    "status": _status_for_binding(report, name),
                    "entry": binding.entry,
                    "runner": binding.runner or "local",
                    "usage": _usage_for_tool(name),
                }
            )

    payload = {"query": query, "count": len(results), "results": results}
    if json_mode:
        print(dumps_pretty(payload))
        return 0

    print(f'Search: "{query}"')
    print(f"Matches: {len(results)}")
    if not results:
        print("No tools found.")
        return 0
    for item in results:
        meta = [f"source: {item['source']}", f"status: {item['status']}"]
        if item.get("pack_id"):
            meta.append(f"pack: {item['pack_id']}")
        if item.get("runner"):
            meta.append(f"runner: {item['runner']}")
        meta_text = ", ".join(meta)
        suffix = f" {meta_text}" if meta_text else ""
        print(f"- {item['name']}{suffix}")
        print(f"  Use: {item['usage']}")
        if item.get("fix"):
            print(f"  Fix: {item['fix']}")
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


def _usage_for_tool(name: str) -> str:
    return f"let result is {name}:"


def _pack_fix(provider) -> str | None:
    if provider.source != "installed_pack":
        return None
    if not provider.verified:
        return f"n3 packs verify {provider.pack_id}"
    if not provider.enabled:
        return f"n3 packs enable {provider.pack_id}"
    return None


def _missing_query_message() -> str:
    return build_guidance_message(
        what="Tool search query is missing.",
        why="n3 tools search needs a search phrase.",
        fix='Provide a query like `n3 tools search "date"`.',
        example='n3 tools search "date"',
    )


def _unknown_args_message(args: list[str]) -> str:
    joined = " ".join(args)
    return build_guidance_message(
        what=f"Unknown arguments: {joined}.",
        why="The tools search command accepts a query and optional app.ai path.",
        fix="Remove the extra arguments and try again.",
        example='n3 tools search "date"',
    )


__all__ = ["run_tools_search"]
