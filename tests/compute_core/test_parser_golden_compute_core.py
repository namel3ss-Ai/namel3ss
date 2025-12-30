from __future__ import annotations

import json
from pathlib import Path

from namel3ss.parser.core import parse
from tests.compute_core.helpers.samples import sample_sources
from tests.spec_freeze.helpers.ast_dump import dump_ast


PARSER_GOLDEN_DIR = Path("tests/golden/compute_core/parser")


def test_parser_golden_compute_core() -> None:
    for name, path, source in sample_sources():
        program = parse(source)
        actual = dump_ast(program)
        fixture_path = PARSER_GOLDEN_DIR / f"{name}.json"
        expected = json.loads(fixture_path.read_text(encoding="utf-8"))
        assert actual == expected, f"AST golden mismatch for {path}"
