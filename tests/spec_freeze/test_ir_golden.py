from __future__ import annotations

import json

from namel3ss.ir.nodes import lower_program
from namel3ss.parser.core import parse
from namel3ss.spec_freeze.v1.rules import IR_GOLDEN_DIR
from tests.spec_freeze.helpers.ir_dump import dump_ir
from tests.spec_freeze.helpers.samples import sample_sources


def test_ir_golden():
    for name, path, source in sample_sources():
        program = lower_program(parse(source))
        actual = dump_ir(program)
        fixture_path = IR_GOLDEN_DIR / f"{name}.json"
        expected = json.loads(fixture_path.read_text(encoding="utf-8"))
        assert actual == expected, f"IR golden mismatch for {path}"
