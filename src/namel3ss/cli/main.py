from __future__ import annotations

import sys

from namel3ss.cli.actions_mode import list_actions
import os

from namel3ss.cli.app_loader import load_program
from namel3ss.cli.format_mode import run_format
from namel3ss.cli.new_mode import run_new
from namel3ss.cli.lint_mode import run_lint
from namel3ss.cli.json_io import dumps_pretty, parse_payload
from namel3ss.cli.runner import run_flow
from namel3ss.cli.ui_mode import render_manifest, run_action
from namel3ss.cli.doctor import run_doctor
from namel3ss.cli.studio_mode import run_studio
from namel3ss.cli.check_mode import run_check
from namel3ss.cli.persist_mode import run_persist
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.render import format_error
from namel3ss.lint.engine import lint_source
from namel3ss.ui.manifest import build_manifest
from namel3ss.version import get_version

RESERVED = {"check", "ui", "flow", "help", "format", "lint", "actions", "studio", "persist"}


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
    try:
        if not args:
            _print_usage()
            return 1

        if args[0] == "--version":
            print(f"namel3ss {get_version()}")
            return 0
        if args[0] == "doctor":
            json_mode = len(args) > 1 and args[1] == "--json"
            return run_doctor(json_mode=json_mode)
        if args[0] == "help":
            _print_usage()
            return 0
        if args[0] == "new":
            return run_new(args[1:])

        path = args[0]
        remainder = args[1:]

        if remainder and remainder[0] == "check":
            allow_aliases = _allow_aliases_from_flags(remainder[1:])
            return run_check(path, allow_legacy_type_aliases=allow_aliases)
        if remainder and remainder[0] == "format":
            check_only = len(remainder) > 1 and remainder[1] == "check"
            return run_format(path, check_only)
        if remainder and remainder[0] == "lint":
            check_only = "check" in remainder[1:]
            strict_types = True
            tail_flags = set(remainder[1:])
            if "no-strict-types" in tail_flags or "relaxed" in tail_flags:
                strict_types = False
            if "strict" in tail_flags:
                strict_types = True
            allow_aliases = _allow_aliases_from_flags(remainder[1:])
            return run_lint(path, check_only, strict_types, allow_aliases)
        if remainder and remainder[0] == "actions":
            json_mode = len(remainder) > 1 and remainder[1] == "json"
            allow_aliases = _allow_aliases_from_flags(remainder)
            program_ir, source = load_program(path, allow_legacy_type_aliases=allow_aliases)
            json_payload, text_output = list_actions(program_ir, json_mode)
            if json_mode:
                print(dumps_pretty(json_payload))
            else:
                print(text_output or "")
            return 0
        if remainder and remainder[0] == "studio":
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
        if remainder and remainder[0] == "persist":
            return run_persist(path, remainder[1:])

        program_ir, source = load_program(path, allow_legacy_type_aliases=_allow_aliases_from_flags([]))
        if not remainder:
            return _run_default(program_ir)
        cmd = remainder[0]
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
        # action mode
        if cmd in RESERVED:
            raise Namel3ssError(
                f"Unknown command: '{cmd}'.\nWhy: command is reserved or out of place.\nFix: run `n3 help` for usage."
            )
        action_id = cmd
        payload_text = tail[0] if tail else "{}"
        payload = parse_payload(payload_text)
        response = run_action(program_ir, action_id, payload)
        print(dumps_pretty(response))
        return 0
    except Namel3ssError as err:
        print(format_error(err, locals().get("source", "")), file=sys.stderr)
        return 1


def _run_default(program_ir) -> int:
    output = run_flow(program_ir, None)
    print(dumps_pretty(output))
    return 0


def _print_usage() -> None:
    usage = """Usage:
  n3 new [template] [name]       # scaffold from a template (omit args to list)
  n3 <app.ai>                      # run default flow
  n3 <app.ai> check                # validate only
  n3 <app.ai> ui                   # print UI manifest
  n3 <app.ai> flow "<name>"        # run specific flow
  n3 <app.ai> format               # format in place
  n3 <app.ai> format check         # check formatting only
  n3 <app.ai> lint                 # lint and print findings
  n3 <app.ai> lint check           # lint, fail on findings
  n3 <app.ai> studio [--port N]    # start Studio viewer (use --dry to skip server in tests)
  n3 <app.ai> studio --dry         # dry run (prints URL)
  n3 <app.ai> persist status       # show persistence mode/path
  n3 <app.ai> persist reset --yes  # reset persisted data (SQLite only)
  n3 <app.ai> actions              # list actions (plain text)
  n3 <app.ai> actions json         # list actions (JSON)
  n3 <app.ai> <action_id> [json]   # execute UI action (payload optional)
  n3 <app.ai> help                 # this help
"""
    print(usage.strip())


if __name__ == "__main__":
    sys.exit(main())
