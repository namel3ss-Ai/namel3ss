from __future__ import annotations

import sys

from namel3ss.cli.app_path import resolve_app_path
from namel3ss.cli.text_output import prepare_cli_text
from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.errors.render import format_error
from namel3ss.marketplace import approve_item, install_item, item_comments, publish_item, rate_item, search_items


KNOWN_OPTIONS = {"--json", "--registry", "--include-pending", "--version", "--comment"}



def run_marketplace_command(args: list[str]) -> int:
    try:
        if not args or args[0] in {"help", "-h", "--help"}:
            _print_usage()
            return 0
        cmd = args[0]
        tail = args[1:]
        if cmd == "publish":
            payload, json_mode = _run_publish(tail)
            return _emit(payload, json_mode)
        if cmd == "search":
            payload, json_mode = _run_search(tail)
            return _emit(payload, json_mode)
        if cmd == "install":
            payload, json_mode = _run_install(tail)
            return _emit(payload, json_mode)
        if cmd == "approve":
            payload, json_mode = _run_approve(tail)
            return _emit(payload, json_mode)
        if cmd == "rate":
            payload, json_mode = _run_rate(tail)
            return _emit(payload, json_mode)
        if cmd == "comments":
            payload, json_mode = _run_comments(tail)
            return _emit(payload, json_mode)
        raise Namel3ssError(
            build_guidance_message(
                what=f"Unknown marketplace command '{cmd}'.",
                why="Supported commands are publish, search, install, approve, rate, and comments.",
                fix="Run n3 marketplace help.",
                example="n3 marketplace search flow",
            )
        )
    except Namel3ssError as err:
        print(prepare_cli_text(format_error(err, None)), file=sys.stderr)
        return 1



def _run_publish(args: list[str]) -> tuple[dict[str, object], bool]:
    json_mode, registry, options, unknown, positional = _parse_args(args)
    _ensure_no_unknown(unknown, "publish")
    _ensure_no_option(options, "--include-pending", "publish")
    _ensure_no_option(options, "--version", "publish")
    _ensure_no_option(options, "--comment", "publish")
    if len(positional) != 1:
        raise Namel3ssError(
            build_guidance_message(
                what="marketplace publish requires exactly one item path.",
                why="Publish needs a folder or manifest path.",
                fix="Pass the path to the item folder.",
                example="n3 marketplace publish ./item",
            )
        )
    app_path = resolve_app_path(None)
    payload = publish_item(
        project_root=app_path.parent,
        app_path=app_path,
        item_path=positional[0],
        registry_override=registry,
    )
    return payload, json_mode



def _run_search(args: list[str]) -> tuple[dict[str, object], bool]:
    json_mode, registry, options, unknown, positional = _parse_args(args)
    _ensure_no_unknown(unknown, "search")
    _ensure_no_option(options, "--version", "search")
    _ensure_no_option(options, "--comment", "search")
    include_pending = bool(options.get("--include-pending"))
    if len(positional) != 1:
        raise Namel3ssError(
            build_guidance_message(
                what="marketplace search needs one query.",
                why="Search requires text input.",
                fix="Provide a search query.",
                example="n3 marketplace search prompt",
            )
        )
    app_path = resolve_app_path(None)
    items = search_items(
        project_root=app_path.parent,
        app_path=app_path,
        query=positional[0],
        include_pending=include_pending,
        registry_override=registry,
    )
    return {"ok": True, "count": len(items), "items": items}, json_mode



def _run_install(args: list[str]) -> tuple[dict[str, object], bool]:
    json_mode, registry, options, unknown, positional = _parse_args(args)
    _ensure_no_unknown(unknown, "install")
    _ensure_no_option(options, "--comment", "install")
    include_pending = bool(options.get("--include-pending"))
    version = str(options.get("--version") or "") or None
    if len(positional) != 1:
        raise Namel3ssError(
            build_guidance_message(
                what="marketplace install needs one item name.",
                why="Install requires the marketplace name.",
                fix="Pass the item name and optional --version.",
                example="n3 marketplace install demo.item --version 0.1.0",
            )
        )
    app_path = resolve_app_path(None)
    payload = install_item(
        project_root=app_path.parent,
        app_path=app_path,
        name=positional[0],
        version=version,
        include_pending=include_pending,
        registry_override=registry,
    )
    return payload, json_mode



def _run_approve(args: list[str]) -> tuple[dict[str, object], bool]:
    json_mode, registry, options, unknown, positional = _parse_args(args)
    _ensure_no_unknown(unknown, "approve")
    _ensure_no_option(options, "--include-pending", "approve")
    _ensure_no_option(options, "--version", "approve")
    _ensure_no_option(options, "--comment", "approve")
    if len(positional) != 2:
        raise Namel3ssError(
            build_guidance_message(
                what="marketplace approve needs item name and version.",
                why="Approve identifies one pending item.",
                fix="Pass name and version.",
                example="n3 marketplace approve demo.item 0.1.0",
            )
        )
    app_path = resolve_app_path(None)
    payload = approve_item(
        project_root=app_path.parent,
        app_path=app_path,
        name=positional[0],
        version=positional[1],
        registry_override=registry,
    )
    return payload, json_mode



def _run_rate(args: list[str]) -> tuple[dict[str, object], bool]:
    json_mode, registry, options, unknown, positional = _parse_args(args)
    _ensure_no_unknown(unknown, "rate")
    _ensure_no_option(options, "--include-pending", "rate")
    _ensure_no_option(options, "--version", "rate")
    comment = str(options.get("--comment") or "")
    if len(positional) != 3:
        raise Namel3ssError(
            build_guidance_message(
                what="marketplace rate needs name, version, and rating.",
                why="Rating records one review entry.",
                fix="Provide all three values.",
                example="n3 marketplace rate demo.item 0.1.0 5 --comment \"Helpful\"",
            )
        )
    try:
        rating = int(positional[2])
    except ValueError as err:
        raise Namel3ssError(
            build_guidance_message(
                what="Rating is invalid.",
                why=f"Could not parse '{positional[2]}'.",
                fix="Use an integer from 1 to 5.",
                example="n3 marketplace rate demo.item 0.1.0 5",
            )
        ) from err
    app_path = resolve_app_path(None)
    payload = rate_item(
        project_root=app_path.parent,
        app_path=app_path,
        name=positional[0],
        version=positional[1],
        rating=rating,
        comment=comment,
        registry_override=registry,
    )
    return payload, json_mode



def _run_comments(args: list[str]) -> tuple[dict[str, object], bool]:
    json_mode, registry, options, unknown, positional = _parse_args(args)
    _ensure_no_unknown(unknown, "comments")
    _ensure_no_option(options, "--include-pending", "comments")
    _ensure_no_option(options, "--version", "comments")
    _ensure_no_option(options, "--comment", "comments")
    if len(positional) != 2:
        raise Namel3ssError(
            build_guidance_message(
                what="marketplace comments needs name and version.",
                why="Comments are tied to one item version.",
                fix="Provide name and version.",
                example="n3 marketplace comments demo.item 0.1.0",
            )
        )
    app_path = resolve_app_path(None)
    comments = item_comments(
        project_root=app_path.parent,
        app_path=app_path,
        name=positional[0],
        version=positional[1],
        registry_override=registry,
    )
    return {"ok": True, "count": len(comments), "comments": comments}, json_mode



def _parse_args(args: list[str]) -> tuple[bool, str | None, dict[str, object], list[str], list[str]]:
    json_mode = False
    registry = None
    options: dict[str, object] = {}
    unknown: list[str] = []
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
                        why="Registry override needs a path.",
                        fix="Provide a path or URL value.",
                        example="n3 marketplace search flow --registry ./registry",
                    )
                )
            registry = args[i + 1]
            i += 2
            continue
        if arg == "--include-pending":
            options[arg] = True
            i += 1
            continue
        if arg in {"--version", "--comment"}:
            if i + 1 >= len(args):
                raise Namel3ssError(
                    build_guidance_message(
                        what=f"{arg} is missing a value.",
                        why="The flag requires a value.",
                        fix=f"Provide a value after {arg}.",
                        example=f"n3 marketplace search flow {arg} demo",
                    )
                )
            options[arg] = args[i + 1]
            i += 2
            continue
        if arg.startswith("--"):
            if arg in KNOWN_OPTIONS:
                unknown.append(arg)
            else:
                unknown.append(arg)
            i += 1
            continue
        positional.append(arg)
        i += 1

    return json_mode, registry, options, unknown, positional



def _ensure_no_unknown(flags: list[str], cmd: str) -> None:
    if flags:
        raise Namel3ssError(_unknown_flags_message(flags[0], cmd))



def _ensure_no_option(options: dict[str, object], key: str, cmd: str) -> None:
    if key in options:
        raise Namel3ssError(_unknown_flags_message(key, cmd))



def _unknown_flags_message(flag: str, cmd: str) -> str:
    return build_guidance_message(
        what=f"Unknown flag '{flag}'.",
        why=f"Unsupported flag for marketplace {cmd}.",
        fix="Remove unsupported flags and retry.",
        example=f"n3 marketplace {cmd} --json",
    )



def _emit(payload: dict[str, object], json_mode: bool) -> int:
    if json_mode:
        print(canonical_json_dumps(payload, pretty=True, drop_run_keys=False))
        return 0
    _print_human(payload)
    return 0



def _print_human(payload: dict[str, object]) -> None:
    if payload.get("items") and isinstance(payload.get("items"), list):
        print(f"Marketplace items: {payload.get('count')}")
        for item in payload.get("items") or []:
            if not isinstance(item, dict):
                continue
            print(
                "  "
                f"{item.get('name')}@{item.get('version')} "
                f"status={item.get('status')} rating={item.get('rating_avg')}"
            )
        return
    if payload.get("comments") and isinstance(payload.get("comments"), list):
        print(f"Comments: {payload.get('count')}")
        for item in payload.get("comments") or []:
            if not isinstance(item, dict):
                continue
            print(f"  rating={item.get('rating')} comment={item.get('comment')}")
        return
    for key in sorted(payload.keys()):
        print(f"{key}: {payload[key]}")



def _print_usage() -> None:
    usage = """Usage:
  n3 marketplace publish <path> [--registry PATH] [--json]
  n3 marketplace search <query> [--include-pending] [--registry PATH] [--json]
  n3 marketplace install <name> [--version VERSION] [--include-pending] [--registry PATH] [--json]
  n3 marketplace approve <name> <version> [--registry PATH] [--json]
  n3 marketplace rate <name> <version> <1-5> [--comment TEXT] [--registry PATH] [--json]
  n3 marketplace comments <name> <version> [--registry PATH] [--json]
"""
    print(usage.strip())


__all__ = ["run_marketplace_command"]
