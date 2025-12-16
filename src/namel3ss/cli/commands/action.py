from __future__ import annotations

import sys

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.render import format_error
from namel3ss.ir.nodes import lower_program
from namel3ss.parser.core import parse
from namel3ss.runtime.store.memory_store import MemoryStore
from namel3ss.runtime.ui.actions import handle_action
from namel3ss.cli.io.json_io import dumps_pretty, parse_json
from namel3ss.cli.io.read_source import read_source


def run(args) -> int:
    source = ""
    try:
        source, _ = read_source(args.path)
        ast_program = parse(source)
        program_ir = lower_program(ast_program)
        payload = parse_json(args.payload or "{}")
        response = handle_action(program_ir, action_id=args.id, payload=payload, state={}, store=MemoryStore())
        print(dumps_pretty(response))
        return 0
    except Namel3ssError as err:
        print(format_error(err, source), file=sys.stderr)
        return 1
