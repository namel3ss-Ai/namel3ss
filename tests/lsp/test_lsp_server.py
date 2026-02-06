from __future__ import annotations

from namel3ss.lsp.server import diagnostics_for_text


def test_lsp_diagnostics_for_valid_source() -> None:
    source = 'spec is "1.0"\n\nflow "demo":\n  return "ok"\n'
    diagnostics = diagnostics_for_text(source)
    assert diagnostics == []


def test_lsp_diagnostics_for_invalid_source() -> None:
    source = 'spec is "1.0"\n\nflow "demo"\n  return "ok"\n'
    diagnostics = diagnostics_for_text(source)
    assert diagnostics
    assert diagnostics[0]["severity"] == 1
