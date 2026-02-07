from __future__ import annotations

import sys

from namel3ss.cli.app_path import default_missing_app_message, resolve_app_path
from namel3ss.cli.devex import parse_project_overrides
from namel3ss.cli.text_output import prepare_cli_text
from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.errors.render import format_error
from namel3ss.plugin.registry import install_plugin, list_plugins, publish_plugin, split_name_and_version
from namel3ss.runtime.capabilities.feature_gate import require_app_capability


def run_plugin_registry_command(args: list[str]) -> int:
    try:
        if not args or args[0] in {"help", "-h", "--help"}:
            _print_usage()
            return 0
        cmd = args[0]
        if cmd == "publish":
            return _run_publish(args[1:])
        if cmd == "install":
            return _run_install(args[1:])
        if cmd == "list":
            return _run_list(args[1:])
        raise Namel3ssError(_unknown_subcommand_message(cmd))
    except Namel3ssError as err:
        print(prepare_cli_text(format_error(err, None)), file=sys.stderr)
        return 1


def _run_publish(args: list[str]) -> int:
    overrides, remaining = parse_project_overrides(args)
    json_mode, registry_override, positional = _parse_common_flags(remaining)
    if len(positional) != 2 or positional[0] != "plugin":
        raise Namel3ssError(_publish_usage_message())
    app_path = _resolve_app_path(overrides)
    _require_plugin_registry_capability(app_path)
    payload = publish_plugin(
        project_root=app_path.parent,
        app_path=app_path,
        plugin_path=positional[1],
        registry_override=registry_override,
    )
    return _emit(payload, json_mode=json_mode)


def _run_install(args: list[str]) -> int:
    overrides, remaining = parse_project_overrides(args)
    json_mode, registry_override, positional = _parse_common_flags(remaining)
    if len(positional) != 2 or positional[0] != "plugin":
        raise Namel3ssError(_install_usage_message())
    app_path = _resolve_app_path(overrides)
    _require_plugin_registry_capability(app_path)
    name, version = split_name_and_version(positional[1])
    payload = install_plugin(
        project_root=app_path.parent,
        app_path=app_path,
        name=name,
        version=version,
        registry_override=registry_override,
    )
    return _emit(payload, json_mode=json_mode)


def _run_list(args: list[str]) -> int:
    overrides, remaining = parse_project_overrides(args)
    json_mode, registry_override, positional = _parse_common_flags(remaining)
    if len(positional) != 1 or positional[0] != "plugins":
        raise Namel3ssError(_list_usage_message())
    app_path = _resolve_app_path(overrides)
    _require_plugin_registry_capability(app_path)
    entries = list_plugins(
        project_root=app_path.parent,
        app_path=app_path,
        registry_override=registry_override,
    )
    payload = {
        "ok": True,
        "count": len(entries),
        "plugins": [entry.to_payload() for entry in entries],
    }
    return _emit(payload, json_mode=json_mode)


def _resolve_app_path(overrides) -> object:
    return resolve_app_path(
        overrides.app_path,
        project_root=overrides.project_root,
        search_parents=False,
        missing_message=default_missing_app_message("plugin registry"),
    )


def _require_plugin_registry_capability(app_path) -> None:
    require_app_capability(app_path, "plugin_registry")


def _parse_common_flags(args: list[str]) -> tuple[bool, str | None, list[str]]:
    json_mode = False
    registry_override: str | None = None
    positional: list[str] = []
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--json":
            json_mode = True
            i += 1
            continue
        if arg == "--registry":
            if i + 1 >= len(args):
                raise Namel3ssError(
                    build_guidance_message(
                        what="--registry is missing a value.",
                        why="Registry override requires a directory path.",
                        fix="Provide a path after --registry.",
                        example="n3 publish plugin ./charts --registry ./registry",
                    )
                )
            registry_override = args[i + 1]
            i += 2
            continue
        if arg.startswith("--"):
            raise Namel3ssError(_unknown_flag_message(arg))
        positional.append(arg)
        i += 1
    return json_mode, registry_override, positional


def _emit(payload: dict[str, object], *, json_mode: bool) -> int:
    if json_mode:
        print(canonical_json_dumps(payload, pretty=True, drop_run_keys=False))
        return 0
    if payload.get("plugins") and isinstance(payload.get("plugins"), list):
        print(f"Plugins: {payload.get('count')}")
        for entry in payload["plugins"]:
            if isinstance(entry, dict):
                print(f"  - {entry.get('name')}@{entry.get('version')} hash={entry.get('hash')}")
        return 0
    for key in sorted(payload.keys()):
        print(f"{key}: {payload[key]}")
    return 0


def _unknown_subcommand_message(subcommand: str) -> str:
    return build_guidance_message(
        what=f"Unknown plugin registry command '{subcommand}'.",
        why="Supported commands are publish, install, and list.",
        fix="Run n3 publish plugin, n3 install plugin, or n3 list plugins.",
        example="n3 list plugins",
    )


def _unknown_flag_message(flag: str) -> str:
    return build_guidance_message(
        what=f"Unknown flag '{flag}'.",
        why="Supported flags are --registry and --json.",
        fix="Remove unsupported flags and retry.",
        example="n3 list plugins --json",
    )


def _publish_usage_message() -> str:
    return build_guidance_message(
        what="publish usage is invalid.",
        why="Expected: n3 publish plugin <path>.",
        fix="Provide plugin keyword and plugin path.",
        example="n3 publish plugin ./charts",
    )


def _install_usage_message() -> str:
    return build_guidance_message(
        what="install usage is invalid.",
        why="Expected: n3 install plugin <name[@version]>.",
        fix="Provide plugin keyword and plugin name.",
        example="n3 install plugin charts@0.1.0",
    )


def _list_usage_message() -> str:
    return build_guidance_message(
        what="list usage is invalid.",
        why="Expected: n3 list plugins.",
        fix="Use plugins plural after list.",
        example="n3 list plugins",
    )


def _print_usage() -> None:
    usage = """Usage:
  n3 publish plugin <path> [--registry PATH] [--json]
  n3 install plugin <name[@version]> [--registry PATH] [--json]
  n3 list plugins [--registry PATH] [--json]
"""
    print(usage.strip())


__all__ = ["run_plugin_registry_command"]
