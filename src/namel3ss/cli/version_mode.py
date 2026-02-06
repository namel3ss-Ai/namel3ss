from __future__ import annotations

from dataclasses import dataclass
import sys

from namel3ss.cli.app_path import resolve_app_path
from namel3ss.cli.text_output import prepare_cli_text
from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.errors.render import format_error
from namel3ss.versioning import (
    add_version,
    deprecate_version,
    list_versions,
    load_version_config,
    parse_entity_ref,
    remove_version,
    save_version_config,
)


@dataclass(frozen=True)
class _VersionCommand:
    subcommand: str
    entity: str | None
    version: str | None
    app_arg: str | None
    json_mode: bool
    target: str | None
    status: str | None
    replacement: str | None
    deprecation_date: str | None


def run_version_command(args: list[str]) -> int:
    try:
        params = _parse_args(args)
        if params.subcommand == "help":
            _print_usage()
            return 0

        app_path = resolve_app_path(params.app_arg)
        config = load_version_config(app_path.parent, app_path)

        if params.subcommand == "list":
            payload = {
                "ok": True,
                "count": 0,
                "items": [],
            }
            rows = list_versions(config)
            payload["count"] = len(rows)
            payload["items"] = rows
            return _emit(payload, json_mode=params.json_mode)

        if params.subcommand == "add":
            kind, name = parse_entity_ref(params.entity or "")
            updated = add_version(
                config,
                kind=kind,
                entity_name=name,
                version=params.version or "",
                target=params.target,
                status=params.status or "active",
                replacement=params.replacement,
                deprecation_date=params.deprecation_date,
            )
            out_path = save_version_config(app_path.parent, app_path, updated)
            payload = {
                "ok": True,
                "action": "add",
                "entity": f"{kind}:{name}",
                "version": params.version,
                "output_path": out_path.as_posix(),
            }
            return _emit(payload, json_mode=params.json_mode)

        if params.subcommand == "deprecate":
            kind, name = parse_entity_ref(params.entity or "")
            updated = deprecate_version(
                config,
                kind=kind,
                entity_name=name,
                version=params.version or "",
                replacement=params.replacement,
                deprecation_date=params.deprecation_date,
            )
            out_path = save_version_config(app_path.parent, app_path, updated)
            payload = {
                "ok": True,
                "action": "deprecate",
                "entity": f"{kind}:{name}",
                "version": params.version,
                "replacement": params.replacement,
                "deprecation_date": params.deprecation_date,
                "output_path": out_path.as_posix(),
            }
            return _emit(payload, json_mode=params.json_mode)

        if params.subcommand == "remove":
            kind, name = parse_entity_ref(params.entity or "")
            updated = remove_version(
                config,
                kind=kind,
                entity_name=name,
                version=params.version or "",
                replacement=params.replacement,
            )
            out_path = save_version_config(app_path.parent, app_path, updated)
            payload = {
                "ok": True,
                "action": "remove",
                "entity": f"{kind}:{name}",
                "version": params.version,
                "output_path": out_path.as_posix(),
            }
            return _emit(payload, json_mode=params.json_mode)

        raise Namel3ssError(_unknown_subcommand_message(params.subcommand))
    except Namel3ssError as err:
        print(prepare_cli_text(format_error(err, None)), file=sys.stderr)
        return 1


def _parse_args(args: list[str]) -> _VersionCommand:
    if not args:
        return _VersionCommand(
            subcommand="list",
            entity=None,
            version=None,
            app_arg=None,
            json_mode=False,
            target=None,
            status=None,
            replacement=None,
            deprecation_date=None,
        )

    subcommand = args[0].strip().lower()
    if subcommand in {"help", "-h", "--help"}:
        return _VersionCommand(
            subcommand="help",
            entity=None,
            version=None,
            app_arg=None,
            json_mode=False,
            target=None,
            status=None,
            replacement=None,
            deprecation_date=None,
        )

    json_mode = False
    target = None
    status = None
    replacement = None
    deprecation_date = None
    positional: list[str] = []

    idx = 1
    while idx < len(args):
        arg = args[idx]
        if arg == "--json":
            json_mode = True
            idx += 1
            continue
        if arg in {"--target", "--status", "--replacement", "--eol"}:
            if idx + 1 >= len(args):
                raise Namel3ssError(_missing_option_value_message(arg))
            value = args[idx + 1]
            if arg == "--target":
                target = value
            elif arg == "--status":
                status = value
            elif arg == "--replacement":
                replacement = value
            elif arg == "--eol":
                deprecation_date = value
            idx += 2
            continue
        if arg.startswith("--"):
            raise Namel3ssError(_unknown_flag_message(arg))
        positional.append(arg)
        idx += 1

    if subcommand == "list":
        app_arg = positional[0] if positional else None
        if len(positional) > 1:
            raise Namel3ssError(_too_many_args_message(subcommand))
        return _VersionCommand(
            subcommand=subcommand,
            entity=None,
            version=None,
            app_arg=app_arg,
            json_mode=json_mode,
            target=target,
            status=status,
            replacement=replacement,
            deprecation_date=deprecation_date,
        )

    if subcommand in {"add", "deprecate", "remove"}:
        if len(positional) < 2:
            raise Namel3ssError(_missing_entity_version_message(subcommand))
        entity = positional[0]
        version = positional[1]
        app_arg = positional[2] if len(positional) >= 3 else None
        if len(positional) > 3:
            raise Namel3ssError(_too_many_args_message(subcommand))
        return _VersionCommand(
            subcommand=subcommand,
            entity=entity,
            version=version,
            app_arg=app_arg,
            json_mode=json_mode,
            target=target,
            status=status,
            replacement=replacement,
            deprecation_date=deprecation_date,
        )

    raise Namel3ssError(_unknown_subcommand_message(subcommand))


def _emit(payload: dict[str, object], *, json_mode: bool) -> int:
    if json_mode:
        print(canonical_json_dumps(payload, pretty=True, drop_run_keys=False))
        return 0
    if payload.get("action"):
        print(f"Version action: {payload.get('action')}")
    if payload.get("entity"):
        print(f"  entity: {payload.get('entity')}")
    if payload.get("version"):
        print(f"  version: {payload.get('version')}")
    if payload.get("output_path"):
        print(f"  output: {payload.get('output_path')}")
    items = payload.get("items")
    if isinstance(items, list):
        print(f"  versions: {len(items)}")
        for item in items:
            if not isinstance(item, dict):
                continue
            print(
                f"  {item.get('kind')} {item.get('entity')}@{item.get('version')} "
                f"status={item.get('status')}"
            )
    return 0


def _print_usage() -> None:
    print(
        "Usage:\n"
        "  n3 version list [app.ai] [--json]\n"
        "  n3 version add <kind:name> <version> [--target NAME] [--status STATUS] [--replacement VERSION] [--eol YYYY-MM-DD] [app.ai] [--json]\n"
        "  n3 version deprecate <kind:name> <version> [--replacement VERSION] [--eol YYYY-MM-DD] [app.ai] [--json]\n"
        "  n3 version remove <kind:name> <version> [--replacement VERSION] [app.ai] [--json]"
    )


def _unknown_subcommand_message(subcommand: str) -> str:
    return build_guidance_message(
        what=f"Unknown version command '{subcommand}'.",
        why="Supported commands are list, add, deprecate, and remove.",
        fix="Use one of the supported commands.",
        example="n3 version list",
    )


def _unknown_flag_message(flag: str) -> str:
    return build_guidance_message(
        what=f"Unknown flag '{flag}'.",
        why="This flag is not supported for version commands.",
        fix="Remove the flag or check version help.",
        example="n3 version help",
    )


def _missing_option_value_message(flag: str) -> str:
    return build_guidance_message(
        what=f"Flag '{flag}' is missing a value.",
        why="This flag needs a value immediately after it.",
        fix="Provide a value for the flag.",
        example=f"n3 version add flow:summarise 2.0 {flag} value",
    )


def _missing_entity_version_message(subcommand: str) -> str:
    return build_guidance_message(
        what=f"version {subcommand} is missing arguments.",
        why="Both entity and version are required.",
        fix="Provide kind:name and version.",
        example=f"n3 version {subcommand} route:list_users 1.0",
    )


def _too_many_args_message(subcommand: str) -> str:
    return build_guidance_message(
        what=f"version {subcommand} has too many arguments.",
        why="Only one optional app path is allowed.",
        fix="Remove extra positional arguments.",
        example=f"n3 version {subcommand} flow:summarise 2.0 app.ai",
    )


__all__ = ["run_version_command"]
