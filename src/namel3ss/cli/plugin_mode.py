from __future__ import annotations

from pathlib import Path

from namel3ss.cli.app_path import default_missing_app_message, resolve_app_path
from namel3ss.cli.devex import parse_project_overrides
from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.plugin.community import (
    extension_info,
    install_registry_extension,
    list_installed_extensions,
    list_registry_extensions,
    revoke_extension_trust,
    search_registry_extensions,
    trust_extension_package,
    update_installed_extension,
)
from namel3ss.plugin.registry import split_name_and_version
from namel3ss.plugin.scaffold import scaffold_plugin
from namel3ss.runtime.capabilities.feature_gate import require_app_capability


def run_plugin_command(args: list[str]) -> int:
    if not args or args[0] in {"help", "-h", "--help"}:
        _print_usage()
        return 0
    cmd = str(args[0]).strip().lower()
    if cmd == "new":
        return _run_new(args[1:])
    if cmd == "search":
        return _run_search(args[1:])
    if cmd == "info":
        return _run_info(args[1:])
    if cmd == "list":
        return _run_list(args[1:])
    if cmd == "install":
        return _run_install(args[1:])
    if cmd == "update":
        return _run_update(args[1:])
    if cmd == "trust":
        return _run_trust(args[1:])
    if cmd == "revoke":
        return _run_revoke(args[1:])
    raise Namel3ssError(
        build_guidance_message(
            what=f"Unknown plugin command '{cmd}'.",
            why="Supported commands are new, search, info, list, install, update, trust, revoke.",
            fix="Run n3 plugin --help and retry.",
            example="n3 plugin search storage",
        )
    )


def _run_new(args: list[str]) -> int:
    if len(args) < 2:
        raise Namel3ssError(_missing_new_args_message())
    if len(args) > 2:
        raise Namel3ssError(_too_many_new_args_message(args[2:]))
    language = args[0]
    name = args[1]
    target = scaffold_plugin(language, name, Path.cwd())
    print(f"Created plugin at {target}")
    print("Next step")
    print(f"  cd {target.name}")
    return 0


def _run_search(args: list[str]) -> int:
    overrides, remaining = parse_project_overrides(args)
    json_mode, registry_override, _installed, allow_yes, positional = _parse_flags(remaining)
    if allow_yes:
        raise Namel3ssError("--yes is not supported for plugin search.")
    if len(positional) != 1:
        raise Namel3ssError(_search_usage_message())
    project_root, app_path = _resolve_project_and_optional_app(overrides)
    entries = search_registry_extensions(
        project_root=project_root,
        app_path=app_path,
        keyword=positional[0],
        registry_override=registry_override,
    )
    payload = {
        "ok": True,
        "count": len(entries),
        "results": [entry.to_payload() for entry in entries],
    }
    return _emit(payload, json_mode=json_mode)


def _run_info(args: list[str]) -> int:
    overrides, remaining = parse_project_overrides(args)
    json_mode, registry_override, _installed, allow_yes, positional = _parse_flags(remaining)
    if allow_yes:
        raise Namel3ssError("--yes is not supported for plugin info.")
    if len(positional) != 1:
        raise Namel3ssError(_info_usage_message())
    project_root, app_path = _resolve_project_and_optional_app(overrides)
    name, version = _split_package_token(positional[0])
    entry = extension_info(
        project_root=project_root,
        app_path=app_path,
        name=name,
        version=version,
        registry_override=registry_override,
    )
    payload = {"ok": True, "plugin": entry.to_payload()}
    return _emit(payload, json_mode=json_mode)


def _run_list(args: list[str]) -> int:
    overrides, remaining = parse_project_overrides(args)
    json_mode, registry_override, installed, allow_yes, positional = _parse_flags(remaining)
    if allow_yes:
        raise Namel3ssError("--yes is not supported for plugin list.")
    if positional:
        raise Namel3ssError(_list_usage_message())
    project_root, app_path = _resolve_project_and_optional_app(overrides)
    if installed:
        entries = list_installed_extensions(project_root=project_root)
    else:
        entries = list_registry_extensions(
            project_root=project_root,
            app_path=app_path,
            registry_override=registry_override,
        )
    payload = {"ok": True, "count": len(entries), "plugins": [entry.to_payload() for entry in entries]}
    return _emit(payload, json_mode=json_mode)


def _run_install(args: list[str]) -> int:
    overrides, remaining = parse_project_overrides(args)
    json_mode, registry_override, installed, allow_yes, positional = _parse_flags(remaining)
    if installed:
        raise Namel3ssError("--installed is not supported for plugin install.")
    if len(positional) != 1:
        raise Namel3ssError(_install_usage_message())
    app_path = _resolve_app_path(overrides, context="plugin install")
    require_app_capability(app_path, "extension_trust")
    payload = install_registry_extension(
        project_root=app_path.parent,
        app_path=app_path,
        package=positional[0],
        registry_override=registry_override,
        allow_untrusted=allow_yes,
    )
    return _emit(payload, json_mode=json_mode)


def _run_update(args: list[str]) -> int:
    overrides, remaining = parse_project_overrides(args)
    json_mode, registry_override, installed, allow_yes, positional = _parse_flags(remaining)
    if installed:
        raise Namel3ssError("--installed is not supported for plugin update.")
    if len(positional) != 1:
        raise Namel3ssError(_update_usage_message())
    app_path = _resolve_app_path(overrides, context="plugin update")
    require_app_capability(app_path, "extension_trust")
    payload = update_installed_extension(
        project_root=app_path.parent,
        app_path=app_path,
        name=positional[0],
        registry_override=registry_override,
        allow_untrusted=allow_yes,
    )
    return _emit(payload, json_mode=json_mode)


def _run_trust(args: list[str]) -> int:
    overrides, remaining = parse_project_overrides(args)
    json_mode, registry_override, installed, allow_yes, positional = _parse_flags(remaining)
    if installed:
        raise Namel3ssError("--installed is not supported for plugin trust.")
    if not allow_yes:
        raise Namel3ssError(
            build_guidance_message(
                what="plugin trust requires explicit confirmation.",
                why="Trusting an extension grants declared permissions locally.",
                fix="Re-run with --yes after reviewing metadata.",
                example="n3 plugin trust charts@0.1.0 --yes",
            )
        )
    if len(positional) != 1:
        raise Namel3ssError(_trust_usage_message())
    app_path = _resolve_app_path(overrides, context="plugin trust")
    require_app_capability(app_path, "extension_trust")
    record = trust_extension_package(
        project_root=app_path.parent,
        app_path=app_path,
        package=positional[0],
        registry_override=registry_override,
    )
    payload = {"ok": True, "trusted": record.to_payload()}
    return _emit(payload, json_mode=json_mode)


def _run_revoke(args: list[str]) -> int:
    overrides, remaining = parse_project_overrides(args)
    json_mode, registry_override, installed, allow_yes, positional = _parse_flags(remaining)
    if registry_override is not None:
        raise Namel3ssError("--registry is not supported for plugin revoke.")
    if installed:
        raise Namel3ssError("--installed is not supported for plugin revoke.")
    if allow_yes:
        raise Namel3ssError("--yes is not supported for plugin revoke.")
    if len(positional) != 1:
        raise Namel3ssError(_revoke_usage_message())
    app_path = _resolve_app_path(overrides, context="plugin revoke")
    require_app_capability(app_path, "extension_trust")
    removed = revoke_extension_trust(project_root=app_path.parent, package=positional[0])
    payload = {"ok": True, "removed": removed, "package": positional[0]}
    return _emit(payload, json_mode=json_mode)


def _parse_flags(args: list[str]) -> tuple[bool, str | None, bool, bool, list[str]]:
    json_mode = False
    registry_override: str | None = None
    installed = False
    allow_yes = False
    positional: list[str] = []
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--json":
            json_mode = True
            i += 1
            continue
        if arg == "--installed":
            installed = True
            i += 1
            continue
        if arg == "--yes":
            allow_yes = True
            i += 1
            continue
        if arg == "--registry":
            if i + 1 >= len(args):
                raise Namel3ssError(_missing_flag_value_message("--registry"))
            registry_override = args[i + 1]
            i += 2
            continue
        if arg.startswith("--"):
            raise Namel3ssError(_unknown_flag_message(arg))
        positional.append(arg)
        i += 1
    return json_mode, registry_override, installed, allow_yes, positional


def _emit(payload: dict[str, object], *, json_mode: bool) -> int:
    if json_mode:
        print(canonical_json_dumps(payload, pretty=True, drop_run_keys=False))
        return 0
    if "plugin" in payload and isinstance(payload["plugin"], dict):
        item = payload["plugin"]
        print(f"{item.get('name')}@{item.get('version')}")
        print(f"trusted: {item.get('trusted')}")
        print(f"permissions: {', '.join(item.get('permissions') or [])}")
        return 0
    if "plugins" in payload and isinstance(payload["plugins"], list):
        print(f"Plugins: {payload.get('count', 0)}")
        for item in payload["plugins"]:
            if not isinstance(item, dict):
                continue
            print(
                f"  - {item.get('name')}@{item.get('version')} "
                f"trusted={item.get('trusted')} hash={item.get('hash')}"
            )
        return 0
    for key in sorted(payload.keys()):
        print(f"{key}: {payload[key]}")
    return 0


def _resolve_project_and_optional_app(overrides) -> tuple[Path, Path | None]:
    if overrides.app_path:
        app_path = resolve_app_path(
            overrides.app_path,
            project_root=overrides.project_root,
            search_parents=False,
            missing_message=default_missing_app_message("plugin"),
        )
        return app_path.parent, app_path
    if overrides.project_root:
        return Path(overrides.project_root).resolve(), None
    return Path.cwd().resolve(), None


def _resolve_app_path(overrides, *, context: str) -> Path:
    return resolve_app_path(
        overrides.app_path,
        project_root=overrides.project_root,
        search_parents=False,
        missing_message=default_missing_app_message(context),
    )


def _split_package_token(value: str) -> tuple[str, str | None]:
    if "@" not in value:
        return str(value).strip(), None
    return split_name_and_version(str(value))


def _missing_new_args_message() -> str:
    return build_guidance_message(
        what="Plugin scaffolding requires a language and name.",
        why="No language or name was provided.",
        fix="Provide a language and plugin name.",
        example="n3 plugin new node demo_plugin",
    )


def _too_many_new_args_message(args: list[str]) -> str:
    extra = " ".join(args)
    return build_guidance_message(
        what=f"Too many arguments: {extra}.",
        why="Plugin scaffolding accepts only language and name.",
        fix="Remove the extra arguments.",
        example="n3 plugin new go demo_plugin",
    )


def _missing_flag_value_message(flag: str) -> str:
    return build_guidance_message(
        what=f"{flag} is missing a value.",
        why=f"{flag} requires a value immediately after the flag.",
        fix="Provide the flag value and retry.",
        example=f"n3 plugin search charts {flag} ./my_registry",
    )


def _unknown_flag_message(flag: str) -> str:
    return build_guidance_message(
        what=f"Unknown flag '{flag}'.",
        why="Supported plugin flags are --json, --registry, --installed, and --yes.",
        fix="Remove unsupported flags.",
        example="n3 plugin list --installed --json",
    )


def _search_usage_message() -> str:
    return build_guidance_message(
        what="plugin search usage is invalid.",
        why="search expects exactly one keyword.",
        fix="Provide a keyword after search.",
        example="n3 plugin search storage",
    )


def _info_usage_message() -> str:
    return build_guidance_message(
        what="plugin info usage is invalid.",
        why="info expects exactly one package token.",
        fix="Provide <name> or <name>@<version>.",
        example="n3 plugin info charts@0.1.0",
    )


def _list_usage_message() -> str:
    return build_guidance_message(
        what="plugin list usage is invalid.",
        why="list does not accept positional arguments.",
        fix="Use flags only.",
        example="n3 plugin list --installed",
    )


def _install_usage_message() -> str:
    return build_guidance_message(
        what="plugin install usage is invalid.",
        why="install expects exactly one package token.",
        fix="Provide <name> or <name>@<version>.",
        example="n3 plugin install charts@0.1.0 --yes",
    )


def _update_usage_message() -> str:
    return build_guidance_message(
        what="plugin update usage is invalid.",
        why="update expects exactly one installed extension name.",
        fix="Provide the extension name.",
        example="n3 plugin update charts --yes",
    )


def _trust_usage_message() -> str:
    return build_guidance_message(
        what="plugin trust usage is invalid.",
        why="trust expects exactly one package token.",
        fix="Provide <name> or <name>@<version>.",
        example="n3 plugin trust charts@0.1.0 --yes",
    )


def _revoke_usage_message() -> str:
    return build_guidance_message(
        what="plugin revoke usage is invalid.",
        why="revoke expects exactly one package token.",
        fix="Provide <name> or <name>@<version>.",
        example="n3 plugin revoke charts@0.1.0",
    )


def _print_usage() -> None:
    usage = """Usage:
  n3 plugin new <language> <name>
  n3 plugin search <keyword> [--registry PATH] [--json]
  n3 plugin info <name[@version]> [--registry PATH] [--json]
  n3 plugin list [--installed] [--registry PATH] [--json]
  n3 plugin install <name[@version]> [--registry PATH] [--yes] [--json]
  n3 plugin update <name> [--registry PATH] [--yes] [--json]
  n3 plugin trust <name[@version]> [--registry PATH] --yes [--json]
  n3 plugin revoke <name[@version]> [--json]
"""
    print(usage.strip())


__all__ = ["run_plugin_command"]
