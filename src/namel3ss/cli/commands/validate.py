from __future__ import annotations

import sys

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.render import format_error
from namel3ss.ir.nodes import lower_program
from namel3ss.parser.core import parse


def run(args) -> int:
    source = ""
    try:
        from namel3ss.cli.io.read_source import read_source

        source, _ = read_source(args.path)
        ast_program = parse(source)
        lower_program(ast_program)
        print("Validation succeeded.")
        return 0
    except Namel3ssError as err:
        print(format_error(err, source), file=sys.stderr)
        return 1
