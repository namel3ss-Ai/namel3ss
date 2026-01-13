from __future__ import annotations

from namel3ss.cli.actions_mode import list_actions
from namel3ss.cli.aliases import canonical_command
from namel3ss.cli.app_loader import load_program
from namel3ss.cli.app_path import resolve_app_path
from namel3ss.cli.check_mode import run_check
from namel3ss.cli.constants import RESERVED
from namel3ss.cli.devex import parse_project_overrides
from namel3ss.cli.editor_mode import run_editor_command
from namel3ss.cli.exists_mode import run_exists_command
from namel3ss.cli.explain_mode import run_explain_command
from namel3ss.cli.exports_mode import run_exports
from namel3ss.cli.fix_mode import run_fix_command
from namel3ss.cli.format_mode import run_format
from namel3ss.cli.graph_mode import run_graph
from namel3ss.cli.how_mode import run_how_command
from namel3ss.cli.json_io import dumps_pretty, parse_payload
from namel3ss.cli.lint_mode import run_lint
from namel3ss.cli.observe_mode import run_observe_command
from namel3ss.cli.persist_mode import run_data, run_persist
from namel3ss.cli.proof_mode import run_proof_command
from namel3ss.cli.runner import run_flow
from namel3ss.cli.secrets_mode import run_secrets_command
from namel3ss.cli.see_mode import run_see_command
from namel3ss.cli.studio_mode import run_studio
from namel3ss.cli.ui_mode import export_ui_contract, render_manifest, run_action
from namel3ss.cli.ui_output import print_payload, print_usage
from namel3ss.cli.verify_mode import run_verify_command
from namel3ss.cli.what_mode import run_what_command
from namel3ss.cli.when_mode import run_when_command
from namel3ss.cli.why_mode import run_why_command
from namel3ss.cli.with_mode import run_with_command
from namel3ss.cli.args import (
    allow_aliases_from_flags,
    extract_app_override,
    resolve_explicit_path
)
from namel3ss.errors.base import Namel3ssError

def run_default(program_ir, *, sources: dict | None = None, json_mode: bool) -> int:
    output = run_flow(program_ir, None, sources=sources)
    print_payload(output, json_mode)
    return 0

def handle_app_commands(path: str | None, remainder: list[str], context: dict | None = None) -> int:
    overrides, remaining = parse_project_overrides(remainder)
    remainder = remaining
    app_override = overrides.app_path
    if path is not None and overrides.app_path:
        raise Namel3ssError(
            "App path was provided twice. Use either an explicit app path or --app, not both."
        )
    if path is not None:
        app_override = path
    app_override, remainder = extract_app_override(remainder, app_override)
    canonical_first = canonical_command(remainder[0]) if remainder else None
    if app_override is None:
        resolved_path = resolve_app_path(app_override, project_root=overrides.project_root)
    elif canonical_first == "check":
        resolved_path = resolve_explicit_path(app_override, overrides.project_root)
    else:
        resolved_path = resolve_app_path(app_override, project_root=overrides.project_root)
    if context is not None:
        context["project_root"] = resolved_path.parent
    if remainder and canonical_first == "check":
        allow_aliases = allow_aliases_from_flags(remainder[1:])
        return run_check(resolved_path.as_posix(), allow_legacy_type_aliases=allow_aliases)
    if remainder and canonical_first == "fmt":
        check_only = len(remainder) > 1 and remainder[1] == "check"
        return run_format(resolved_path.as_posix(), check_only)
    if remainder and canonical_first == "lint":
        check_only = "check" in remainder[1:]
        strict_types = True
        tail_flags = set(remainder[1:])
        if "no-strict-types" in tail_flags or "relaxed" in tail_flags:
            strict_types = False
        if "strict" in tail_flags:
            strict_types = True
        strict_tools = "--strict-tools" in remainder[1:]
        allow_aliases = allow_aliases_from_flags(remainder[1:])
        return run_lint(resolved_path.as_posix(), check_only, strict_types, allow_aliases, strict_tools)
    if remainder and canonical_first == "actions":
        json_mode = len(remainder) > 1 and remainder[1] == "json"
        allow_aliases = allow_aliases_from_flags(remainder)
        program_ir, sources = load_program(resolved_path.as_posix(), allow_legacy_type_aliases=allow_aliases)
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
        payload, text_output = run_graph(resolved_path.as_posix(), json_mode=json_mode)
        if json_mode:
            print(dumps_pretty(payload))
        else:
            print(text_output or "")
        return 0
    if remainder and canonical_first == "exports":
        json_mode = len(remainder) > 1 and remainder[1] == "--json"
        payload, text_output = run_exports(resolved_path.as_posix(), json_mode=json_mode)
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
        return run_studio(resolved_path.as_posix(), port, dry)
    if remainder and canonical_first in {"data", "persist"}:
        tail = remainder[1:]
        return run_data(resolved_path.as_posix(), tail) if canonical_first == "data" else run_persist(resolved_path.as_posix(), tail)

    program_ir, sources = load_program(resolved_path.as_posix(), allow_legacy_type_aliases=allow_aliases_from_flags([]))
    if context is not None:
        context["sources"] = sources
    if not remainder:
        return run_default(program_ir, sources=sources, json_mode=False)
    if remainder[0] == "--json" and len(remainder) == 1:
        return run_default(program_ir, sources=sources, json_mode=True)
    
    cmd = canonical_command(remainder[0])
    tail = remainder[1:]
    path_posix = resolved_path.as_posix() # Assuming resolved_path is a Path object from resolve_app_path
    
    if cmd == "ui":
        if tail and tail[0] == "export":
            result = export_ui_contract(program_ir)
            print(dumps_pretty(result))
            return 0
        manifest = render_manifest(program_ir)
        print(dumps_pretty(manifest))
        return 0
    if cmd == "flow":
        json_mode = "--json" in tail
        tail = [item for item in tail if item != "--json"]
        if not tail:
            raise Namel3ssError('Missing flow name. Use: n3 app.ai flow "flow_name"')
        flow_name = tail[0]
        output = run_flow(program_ir, flow_name, sources=sources)
        print_payload(output, json_mode)
        return 0
    if cmd == "help":
        print_usage()
        return 0
    if cmd == "proof":
        return run_proof_command([path_posix, *tail])
    if cmd == "verify":
        return run_verify_command([path_posix, *tail])
    if cmd == "secrets":
        return run_secrets_command([path_posix, *tail])
    if cmd == "observe":
        return run_observe_command([path_posix, *tail])
    if cmd == "explain":
        return run_explain_command([path_posix, *tail])
    if cmd == "editor":
        return run_editor_command([path_posix, *tail])
    # Note: reserved check needs to handle the fact that some commands might be valid here if context is loaded.
    # But original code had this check.
    if cmd in RESERVED:
        raise Namel3ssError(
            f"Unknown command: '{remainder[0]}'.\nWhy: command is reserved or out of place.\nFix: run `n3 help` for usage."
        )
    action_id = remainder[0]
    json_mode = "--json" in tail
    tail = [item for item in tail if item != "--json"]
    payload_text = tail[0] if tail else "{}"
    payload = parse_payload(payload_text)
    response = run_action(program_ir, action_id, payload)
    print_payload(response, json_mode)
    return 0
