from __future__ import annotations

from namel3ss.parser.core import parse
from namel3ss.parser.generated import GRAMMAR_PATH, GRAMMAR_SHA256, RULE_NAMES


def test_generated_parser_backend_matches_legacy_parser() -> None:
    source = 'spec is "1.0"\n\nflow "demo":\n  return "ok"\n'
    generated = parse(source)
    legacy = parse(source, use_old_parser=True)
    assert generated.spec_version == legacy.spec_version
    assert [flow.name for flow in generated.flows] == [flow.name for flow in legacy.flows]


def test_grammar_snapshot_metadata_present() -> None:
    assert GRAMMAR_PATH.endswith("namel3ss.grammar")
    assert len(GRAMMAR_SHA256) == 64
    assert "program" in RULE_NAMES
