from __future__ import annotations

from pathlib import Path

from namel3ss.cli.app_loader import load_program
from namel3ss.cli.app_path import resolve_app_path
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.cli.tools_support import (
    SUPPORTED_CONVENTIONS,
    bindings_payload,
    build_dry_payload,
    missing_entry_message,
    missing_tool_message,
    parse_from_app_args,
    plan_stub,
    print_dry_run,
    stub_conflict_message,
    unknown_args_message,
    unknown_convention_message,
    unknown_flag_message,
)
from namel3ss.runtime.tools.bindings import bindings_path, load_tool_bindings, write_tool_bindings
from namel3ss.runtime.tools.bindings_yaml import ToolBinding, render_bindings_yaml
from namel3ss.runtime.tools.entry_validation import validate_python_tool_entry_exists
from namel3ss.utils.json_tools import dumps_pretty
from namel3ss.utils.slugify import slugify_tool_name

def run_tools(args: list[str]) -> int:
    if not args or args[0] in {"help", "-h", "--help"}:
        _print_usage()
        return 0

    cmd = args[0]
    tail = args[1:]
    json_mode = "--json" in tail
    tail = [item for item in tail if item != "--json"]

    if cmd == "status":
        return _run_status(tail, json_mode=json_mode)
    if cmd == "bind":
        return _run_bind(tail, json_mode=json_mode)
    if cmd == "unbind":
        return _run_unbind(tail, json_mode=json_mode)
    if cmd == "format":
        return _run_format(tail, json_mode=json_mode)

    raise Namel3ssError(
        build_guidance_message(
            what=f"Unknown tools command '{cmd}'.",
            why="Supported commands are status, bind, unbind, and format.",
            fix="Run `n3 tools help` to see usage.",
            example="n3 tools status",
        )
    )


def _run_status(args: list[str], *, json_mode: bool) -> int:
    app_path, extra = _extract_app_path(args)
    if extra:
        raise Namel3ssError(unknown_args_message(extra))
    app_path = resolve_app_path(app_path)
    program, _ = load_program(str(app_path))
    app_root = app_path.parent
    bindings_file = bindings_path(app_root)
    bindings_present = bindings_file.exists()
    bindings_error = None
    bindings_valid = True
    try:
        bindings = load_tool_bindings(app_root)
    except Namel3ssError as err:
        bindings = {}
        bindings_valid = False
        bindings_error = str(err)

    tool_names = sorted(program.tools.keys())
    python_tools = sorted(name for name, tool in program.tools.items() if tool.kind == "python")
    missing = sorted(name for name in python_tools if name not in bindings)
    unused = sorted(name for name in bindings if name not in program.tools)

    payload = {
        "app_root": str(app_root),
        "bindings_path": str(bindings_file),
        "bindings_present": bindings_present,
        "bindings_valid": bindings_valid,
        "bindings_error": bindings_error,
        "tools_declared": tool_names,
        "python_tools": python_tools,
        "missing_bindings": missing,
        "unused_bindings": unused,
        "bindings": bindings_payload(bindings),
    }
    if json_mode:
        print(dumps_pretty(payload))
        return 0

    print(f"App root: {payload['app_root']}")
    print(f"Bindings: {payload['bindings_path']} ({'present' if bindings_present else 'missing'})")
    if not bindings_valid and bindings_error:
        print("Bindings file invalid:")
        print(bindings_error)
    print(f"Declared tools: {len(tool_names)}")
    if python_tools:
        print(f"Python tools: {len(python_tools)}")
    if missing:
        print("Missing bindings:")
        for name in missing:
            print(f"- {name}")
    if unused:
        print("Unused bindings:")
        for name in unused:
            print(f"- {name}")
    return 0


def _run_bind(args: list[str], *, json_mode: bool) -> int:
    if "--from-app" in args:
        return _run_bind_from_app(args, json_mode=json_mode)
    return _run_bind_single(args, json_mode=json_mode)


def _run_bind_single(args: list[str], *, json_mode: bool) -> int:
    tool_name, entry = _parse_bind_args(args)
    app_path = resolve_app_path(None)
    program, _ = load_program(str(app_path))
    if tool_name not in program.tools:
        raise Namel3ssError(
            build_guidance_message(
                what=f'Tool "{tool_name}" is not declared.',
                why="Bindings can only be created for declared tools.",
                fix="Add the tool declaration to app.ai first.",
                example=f'tool "{tool_name}":\n  implemented using python',
            )
        )
    tool_decl = program.tools[tool_name]
    if tool_decl.kind != "python":
        raise Namel3ssError(
            build_guidance_message(
                what=f'Tool "{tool_name}" is not a python tool.',
                why=f"Tool kind is '{tool_decl.kind}'.",
                fix="Bind entries only for python tools.",
                example=f'tool "{tool_name}":\n  implemented using python',
            )
        )
    app_root = app_path.parent
    validate_python_tool_entry_exists(entry, tool_name, app_root=app_root, line=tool_decl.line, column=tool_decl.column)

    bindings = load_tool_bindings(app_root)
    existing = bindings.get(tool_name)
    updated = existing is not None and existing.entry != entry
    bindings[tool_name] = ToolBinding(
        kind="python",
        entry=entry,
        purity=existing.purity if existing else None,
        timeout_ms=existing.timeout_ms if existing else None,
    )
    path = write_tool_bindings(app_root, bindings)
    payload = {
        "status": "ok",
        "tool_name": tool_name,
        "entry": entry,
        "updated": updated,
        "bindings_path": str(path),
    }
    if json_mode:
        print(dumps_pretty(payload))
        return 0
    if updated:
        print(f"Updated binding '{tool_name}' -> {entry}")
    else:
        print(f"Bound tool '{tool_name}' -> {entry}")
    print(f"Bindings file: {path}")
    return 0


def _run_bind_from_app(args: list[str], *, json_mode: bool) -> int:
    config = parse_from_app_args(args)
    app_path = resolve_app_path(config.app_path)
    program, _ = load_program(str(app_path))
    app_root = app_path.parent
    bindings = load_tool_bindings(app_root)

    if config.convention not in SUPPORTED_CONVENTIONS:
        raise Namel3ssError(unknown_convention_message(config.convention))

    python_tools = {name: tool for name, tool in program.tools.items() if tool.kind == "python"}
    missing = sorted(name for name in python_tools if name not in bindings)
    proposed = dict(bindings)
    stubs: list[StubPlan] = []
    for name in missing:
        slug = slugify_tool_name(name)
        entry = f"tools.{slug}:run"
        proposed[name] = ToolBinding(kind="python", entry=entry)
        stub = plan_stub(app_root, python_tools[name], name, slug)
        if stub:
            stubs.append(stub)

    conflicts = [stub.path for stub in stubs if stub.exists and not config.allow_overwrite]
    preview = render_bindings_yaml(proposed)

    if config.dry:
        payload = build_dry_payload(app_root, missing, stubs, preview, conflicts)
        if json_mode:
            print(dumps_pretty(payload))
        else:
            print_dry_run(payload)
        return 0

    if conflicts:
        raise Namel3ssError(stub_conflict_message(conflicts))

    for stub in stubs:
        if stub.exists and config.allow_overwrite:
            stub.path.write_text(stub.content, encoding="utf-8")
        elif not stub.exists:
            stub.path.parent.mkdir(parents=True, exist_ok=True)
            stub.path.write_text(stub.content, encoding="utf-8")

    path = write_tool_bindings(app_root, proposed)
    payload = {
        "status": "ok",
        "bindings_path": str(path),
        "missing_bound": missing,
        "stubs_written": [str(stub.path) for stub in stubs if (stub.exists is False) or config.allow_overwrite],
    }
    if json_mode:
        print(dumps_pretty(payload))
        return 0
    if missing:
        print(f"Bound {len(missing)} tools from app.ai.")
    else:
        print("No missing bindings found.")
    if stubs:
        print("Tool stubs:")
        for stub in stubs:
            status = "overwritten" if stub.exists and config.allow_overwrite else "created" if not stub.exists else "skipped"
            print(f"- {stub.path} ({status})")
    print(f"Bindings file: {path}")
    return 0


def _run_unbind(args: list[str], *, json_mode: bool) -> int:
    if not args:
        raise Namel3ssError(missing_tool_message())
    if len(args) > 1:
        raise Namel3ssError(unknown_args_message(args[1:]))
    tool_name = args[0]
    app_path = resolve_app_path(None)
    app_root = app_path.parent
    bindings = load_tool_bindings(app_root)
    if tool_name not in bindings:
        raise Namel3ssError(
            build_guidance_message(
                what=f'Tool "{tool_name}" is not bound.',
                why="No matching entry was found in .namel3ss/tools.yaml.",
                fix="Check bindings with `n3 tools status`.",
                example=f'n3 tools unbind "{tool_name}"',
            )
        )
    bindings.pop(tool_name)
    path = write_tool_bindings(app_root, bindings)
    payload = {"status": "ok", "tool_name": tool_name, "bindings_path": str(path)}
    if json_mode:
        print(dumps_pretty(payload))
        return 0
    print(f"Removed binding for '{tool_name}'.")
    print(f"Bindings file: {path}")
    return 0


def _run_format(args: list[str], *, json_mode: bool) -> int:
    app_path, extra = _extract_app_path(args)
    if extra:
        raise Namel3ssError(unknown_args_message(extra))
    app_path = resolve_app_path(app_path)
    app_root = app_path.parent
    bindings_file = bindings_path(app_root)
    if not bindings_file.exists():
        raise Namel3ssError(
            build_guidance_message(
                what="Bindings file not found.",
                why="No .namel3ss/tools.yaml exists in this app.",
                fix="Generate bindings with `n3 tools bind --from-app`.",
                example="n3 tools bind --from-app",
            )
        )
    bindings = load_tool_bindings(app_root)
    path = write_tool_bindings(app_root, bindings)
    payload = {"status": "ok", "bindings_path": str(path)}
    if json_mode:
        print(dumps_pretty(payload))
        return 0
    print(f"Formatted bindings file: {path}")
    return 0


def _parse_bind_args(args: list[str]) -> tuple[str, str]:
    tool_name = None
    entry = None
    idx = 0
    while idx < len(args):
        item = args[idx]
        if item in {"--entry", "-e"}:
            if idx + 1 >= len(args):
                raise Namel3ssError(missing_entry_message())
            entry = args[idx + 1]
            idx += 2
            continue
        if item.startswith("--entry="):
            entry = item.split("=", 1)[1]
            idx += 1
            continue
        if item.startswith("-"):
            raise Namel3ssError(unknown_flag_message(item))
        if tool_name is None:
            tool_name = item
        else:
            raise Namel3ssError(
                build_guidance_message(
                    what="Multiple tool names provided.",
                    why="n3 tools bind accepts a single tool name.",
                    fix="Pass only one tool name.",
                    example='n3 tools bind "get data" --entry "tools.http:get_json"',
                )
            )
        idx += 1
    if not tool_name:
        raise Namel3ssError(missing_tool_message())
    if not entry:
        raise Namel3ssError(missing_entry_message())
    return tool_name, entry


def _extract_app_path(args: list[str]) -> tuple[str | None, list[str]]:
    if args and args[0].endswith(".ai"):
        return args[0], args[1:]
    return None, args


def _print_usage() -> None:
    usage = """Usage:
  n3 tools status [app.ai] [--json]
  n3 tools bind "<tool name>" --entry "module:function" [--json]
  n3 tools bind --from-app [app.ai] [--convention slug-run] [--dry] [--yes] [--overwrite] [--json]
  n3 tools unbind "<tool name>" [--json]
  n3 tools format [app.ai] [--json]
"""
    print(usage.strip())


__all__ = ["run_tools"]
