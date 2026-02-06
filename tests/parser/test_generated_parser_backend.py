from __future__ import annotations

from namel3ss.parser.core import parse
from namel3ss.parser.generated import GRAMMAR_PATH, GRAMMAR_SHA256, RULE_NAMES


def test_generated_parser_backend_parses_basic_program() -> None:
    source = 'spec is "1.0"\n\nflow "demo":\n  return "ok"\n'
    generated = parse(source)
    assert generated.spec_version == "1.0"
    assert [flow.name for flow in generated.flows] == ["demo"]


def test_grammar_snapshot_metadata_present() -> None:
    assert GRAMMAR_PATH.endswith("namel3ss.grammar")
    assert len(GRAMMAR_SHA256) == 64
    assert "program" in RULE_NAMES
