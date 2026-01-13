from __future__ import annotations

import sys
from pathlib import Path

from namel3ss.config.loader import load_config
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.render import format_error
from namel3ss.cli.text_output import prepare_cli_text
from namel3ss.ir.nodes import lower_program
from namel3ss.parser.core import parse
from namel3ss.runtime.identity.context import resolve_identity
from namel3ss.ui.manifest import build_manifest
from namel3ss.cli.io.json_io import dumps_pretty
from namel3ss.cli.io.read_source import read_source
from namel3ss.validation import ValidationMode


def run(args) -> int:
    source = ""
    warnings = []
    try:
        source, _ = read_source(args.path)
        ast_program = parse(source)
        program_ir = lower_program(ast_program)
        config = load_config(app_path=Path(args.path))
        identity = resolve_identity(
            config,
            getattr(program_ir, "identity", None),
            mode=ValidationMode.STATIC,
            warnings=warnings,
        )
        manifest = build_manifest(
            program_ir,
            state={},
            store=None,
            identity=identity,
            mode=ValidationMode.STATIC,
            warnings=warnings,
        )
        if warnings:
            manifest["warnings"] = [warning.to_dict() for warning in warnings]
        print(dumps_pretty(manifest))
        return 0
    except Namel3ssError as err:
        print(prepare_cli_text(format_error(err, source)), file=sys.stderr)
        return 1
