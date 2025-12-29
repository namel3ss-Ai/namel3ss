from __future__ import annotations

import json

from namel3ss.parser.core import parse
from namel3ss.spec_freeze.v1.rules import PARSER_GOLDEN_DIR
from tests.spec_freeze.helpers.ast_dump import dump_ast
from tests.spec_freeze.helpers.samples import sample_sources


def test_parser_golden():
    for name, path, source in sample_sources():
        program = parse(source)
        actual = dump_ast(program)
        fixture_path = PARSER_GOLDEN_DIR / f"{name}.json"
        expected = json.loads(fixture_path.read_text(encoding="utf-8"))
        assert actual == expected, f"AST golden mismatch for {path}"
