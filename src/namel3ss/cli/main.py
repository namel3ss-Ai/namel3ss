from __future__ import annotations

import os
import sys

from namel3ss.cli.actions_mode import list_actions
from namel3ss.cli.aliases import canonical_command
from namel3ss.cli.app_path import resolve_app_path
from namel3ss.cli.app_loader import load_program
from namel3ss.cli.build_mode import run_build_command
from namel3ss.cli.check_mode import run_check
from namel3ss.cli.doctor import run_doctor
from namel3ss.cli.exports_mode import run_exports
from namel3ss.cli.format_mode import run_format
from namel3ss.cli.graph_mode import run_graph
from namel3ss.cli.json_io import dumps_pretty, parse_payload
from namel3ss.cli.lint_mode import run_lint
from namel3ss.cli.new_mode import run_new
from namel3ss.cli.persist_mode import run_data, run_persist
from namel3ss.cli.promote_mode import run_promote_command
from namel3ss.cli.run_mode import run_run_command
from namel3ss.cli.runner import run_flow
from namel3ss.cli.status_mode import run_status_command
from namel3ss.cli.studio_mode import run_studio
from namel3ss.cli.test_mode import run_test_command
from namel3ss.cli.ui_mode import render_manifest, run_action
from namel3ss.cli.pkg_mode import run_pkg
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.render import format_error
from namel3ss.version import get_version

RESERVED = {
    "check",
    "ui",
    "flow",
    "help",
    "format",
    "fmt",
    "lint",
    "actions",
    "studio",
    "persist",
    "data",
    "graph",
    "exports",
    "test",
    "pkg",
    "deps",
    "pack",
    "build",
    "ship",
    "promote",
    "where",
    "status",
    "run",
}

ROOT_APP_COMMANDS = {"check", "ui", "actions", "studio", "fmt", "format", "lint", "graph", "exports", "data", "persist"}


def _allow_aliases_from_flags(flags: list[str]) -> bool:
    env_disallow = os.getenv("N3_NO_LEGACY_TYPE_ALIASES")
    allow_aliases = True
    if env_disallow and env_disallow.lower() in {"1", "true", "yes"}:
        allow_aliases = False
    if "--no-legacy-type-aliases" in flags:
        allow_aliases = False
    if "--allow-legacy-type-aliases" in flags:
        allow_aliases = True
    return allow_aliases


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    context: dict = {}
    try:
        if not args:
            _print_usage()
            return 1

        cmd_raw = args[0]
        cmd = canonical_command(cmd_raw)

        if cmd_raw == "--version":
            print(f"namel3ss {get_version()}")
            return 0
        if cmd_raw in {"--help", "-h"}:
            _print_usage()
            return 0
        if cmd == "doctor":
            json_mode = len(args) > 1 and args[1] == "--json"
            return run_doctor(json_mode=json_mode)
        if cmd == "help":
            _print_usage()
            return 0
        if cmd == "run":
            return run_run_command(args[1:])
        if cmd == "pack":
            return run_build_command(args[1:])
        if cmd == "ship":
            return run_promote_command(args[1:])
        if cmd == "where":
            return run_status_command(args[1:])
        if cmd in {"data", "persist"}:
            return run_data(None, args[1:]) if cmd == "data" else run_persist(None, args[1:])
        if cmd in {"pkg", "deps"}:
            return run_pkg(args[1:])
        if cmd == "new":
            return run_new(args[1:])
        if cmd == "test":
            json_mode = len(args) > 1 and args[1] == "--json"
            return run_test_command(json_mode=json_mode)
        if cmd in ROOT_APP_COMMANDS:
            resolved = resolve_app_path(None)
            return _handle_app_commands(resolved.as_posix(), [cmd, *args[1:]], context)

        path = args[0]
        remainder = args[1:]
        return _handle_app_commands(path, remainder, context)
    except Namel3ssError as err:
        print(format_error(err, context.get("sources", "")), file=sys.stderr)
        return 1


def _run_default(program_ir) -> int:
    output = run_flow(program_ir, None)
    print(dumps_pretty(output))
    return 0


def _handle_app_commands(path: str, remainder: list[str], context: dict | None = None) -> int:
    canonical_first = canonical_command(remainder[0]) if remainder else None
    if remainder and canonical_first == "check":
        allow_aliases = _allow_aliases_from_flags(remainder[1:])
        return run_check(path, allow_legacy_type_aliases=allow_aliases)
    if remainder and canonical_first == "fmt":
        check_only = len(remainder) > 1 and remainder[1] == "check"
        return run_format(path, check_only)
    if remainder and canonical_first == "lint":
        check_only = "check" in remainder[1:]
        strict_types = True
        tail_flags = set(remainder[1:])
        if "no-strict-types" in tail_flags or "relaxed" in tail_flags:
            strict_types = False
        if "strict" in tail_flags:
            strict_types = True
        allow_aliases = _allow_aliases_from_flags(remainder[1:])
        return run_lint(path, check_only, strict_types, allow_aliases)
    if remainder and canonical_first == "actions":
        json_mode = len(remainder) > 1 and remainder[1] == "json"
        allow_aliases = _allow_aliases_from_flags(remainder)
        program_ir, sources = load_program(path, allow_legacy_type_aliases=allow_aliases)
        if context is not None:
            context["sources"] = sources
        json_payload, text_output = list_actions(program_ir, json_mode)
        if json_mode:
            print(dumps_pretty(json_payload))
        else:
            print(text_output or "")
        return 0
    if remainder and canonical_first == "graph":
        json_mode = len(remainder) > 1 and remainder[1] == "--json"
        payload, text_output = run_graph(path, json_mode=json_mode)
        if json_mode:
            print(dumps_pretty(payload))
        else:
            print(text_output or "")
        return 0
    if remainder and canonical_first == "exports":
        json_mode = len(remainder) > 1 and remainder[1] == "--json"
        payload, text_output = run_exports(path, json_mode=json_mode)
        if json_mode:
            print(dumps_pretty(payload))
        else:
            print(text_output or "")
        return 0
    if remainder and canonical_first == "studio":
        port = 7333
        dry = False
        tail = remainder[1:]
        i = 0
        while i < len(tail):
            if tail[i] == "--port" and i + 1 < len(tail):
                try:
                    port = int(tail[i + 1])
                except ValueError:
                    raise Namel3ssError("Port must be an integer")
                i += 2
                continue
            if tail[i] == "--dry":
                dry = True
                i += 1
                continue
            i += 1
        return run_studio(path, port, dry)
    if remainder and canonical_first in {"data", "persist"}:
        tail = remainder[1:]
        return run_data(path, tail) if canonical_first == "data" else run_persist(path, tail)

    program_ir, sources = load_program(path, allow_legacy_type_aliases=_allow_aliases_from_flags([]))
    if context is not None:
        context["sources"] = sources
    if not remainder:
        return _run_default(program_ir)
    cmd = canonical_command(remainder[0])
    tail = remainder[1:]
    if cmd == "ui":
        manifest = render_manifest(program_ir)
        print(dumps_pretty(manifest))
        return 0
    if cmd == "flow":
        if not tail:
            raise Namel3ssError('Missing flow name. Use: n3 <app.ai> flow "<name>"')
        flow_name = tail[0]
        output = run_flow(program_ir, flow_name)
        print(dumps_pretty(output))
        return 0
    if cmd == "help":
        _print_usage()
        return 0
    if cmd in RESERVED:
        raise Namel3ssError(
            f"Unknown command: '{remainder[0]}'.\nWhy: command is reserved or out of place.\nFix: run `n3 help` for usage."
        )
    action_id = remainder[0]
    payload_text = tail[0] if tail else "{}"
    payload = parse_payload(payload_text)
    response = run_action(program_ir, action_id, payload)
    print(dumps_pretty(response))
    return 0


def _print_usage() -> None:
    usage = """Usage:
  n3 new [template] [name]         # scaffold from a template (omit args to list)
  n3 run [app.ai] [--target T]     # run app.ai (auto-detects app.ai)
  n3 pack [app.ai] [--target T]    # build artifacts (alias: build)
  n3 ship [--to T|--back]          # promote build (alias: promote; --rollback alias of --back)
  n3 where [app.ai]                # show active target/build (alias: status)
  n3 check [app.ai]                # validate (alias: n3 <app.ai> check)
  n3 ui [app.ai]                   # print UI manifest
  n3 actions [app.ai] [json]       # list actions
  n3 studio [app.ai] [--port N]    # start Studio viewer (use --dry to skip server in tests)
  n3 fmt [app.ai] [check]          # format in place (alias: format)
  n3 lint [app.ai] [check]         # lint
  n3 graph [app.ai] [--json]       # module dependency graph
  n3 exports [app.ai] [--json]     # module export list
  n3 data [app.ai] <cmd>           # data store status/reset (alias: persist)
  n3 deps <cmd> [--json]           # packages (capsules) (alias: pkg)
  n3 <app.ai>                      # run default flow
  n3 <app.ai> <action_id> [json]   # execute UI action (payload optional)
  n3 help                          # this help
  Aliases/legacy: build, promote, status, persist, format, pkg
"""
    print(usage.strip())


if __name__ == "__main__":
    sys.exit(main())
