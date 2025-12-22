from __future__ import annotations

import sys

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.render import format_error
from namel3ss.ir.nodes import lower_program
from namel3ss.parser.core import parse
from namel3ss.runtime.executor import execute_program_flow
from namel3ss.runtime.store.memory_store import MemoryStore
from namel3ss.cli.io.json_io import dumps_pretty
from namel3ss.cli.io.read_source import read_source
from namel3ss.runtime.preferences.factory import preference_store_for_app, app_pref_key


def run(args) -> int:
    source = ""
    try:
        source, path = read_source(args.path)
        ast_program = parse(source)
        program_ir = lower_program(ast_program)
        flow_name = _select_flow(program_ir, args.flow)
        pref_store = preference_store_for_app(path, getattr(program_ir, "theme_preference", {}).get("persist"))
        pref_key = app_pref_key(path)
        initial_theme = None
        if getattr(program_ir, "theme_preference", {}).get("allow_override") and getattr(program_ir, "theme_preference", {}).get("persist") == "file":
            initial_theme = pref_store.load_theme(pref_key)
        result = execute_program_flow(
            program_ir,
            flow_name,
            state={},
            input={},
            store=MemoryStore(),
            runtime_theme=initial_theme or getattr(program_ir, "theme", None),
            preference_store=pref_store,
            preference_key=pref_key,
        )
        traces = [_trace_to_dict(t) for t in result.traces]
        output = {"ok": True, "state": result.state, "result": result.last_value, "traces": traces}
        print(dumps_pretty(output))
        return 0
    except Namel3ssError as err:
        print(format_error(err, source), file=sys.stderr)
        return 1


def _select_flow(program_ir, flow_flag: str | None) -> str:
    if flow_flag:
        return flow_flag
    if len(program_ir.flows) == 1:
        return program_ir.flows[0].name
    raise Namel3ssError("Multiple flows found; specify --flow")


def _trace_to_dict(trace) -> dict:
    if hasattr(trace, "__dict__"):
        return trace.__dict__
    return trace if isinstance(trace, dict) else {"value": trace}
