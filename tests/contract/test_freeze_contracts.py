from __future__ import annotations

import re
from pathlib import Path

from namel3ss.traces.schema import TraceEventType


def test_grammar_contract_lists_frozen_constructs() -> None:
    text = Path("docs/language/grammar_contract.md").read_text(encoding="utf-8")
    assert "## Frozen constructs" in text
    for required in ["spec", "flow", "tool", "policy", "record", "page", "ui"]:
        assert re.search(rf"\b{re.escape(required)}\b", text)


def test_public_contract_freeze_doc_lists_domains() -> None:
    text = Path("docs/contract-freeze.md").read_text(encoding="utf-8")
    for required in [
        "CLI commands",
        "Explain and audit",
        "Observability outputs",
        "Template contracts",
        "Studio stable UI surfaces",
    ]:
        assert required in text


def test_schema_contract_mentions_capability_check() -> None:
    schema_text = Path("docs/trace-schema.md").read_text(encoding="utf-8")
    assert "capability_check" in schema_text
    assert TraceEventType.CAPABILITY_CHECK == "capability_check"


def test_cli_help_fixture_is_present_and_stable() -> None:
    help_text = Path("tests/fixtures/cli/help.txt").read_text(encoding="utf-8")
    assert help_text.strip()
    assert "Usage:" in help_text
    assert "n3" in help_text


def test_studio_guardrail_invariants_snapshot() -> None:
    html = Path("src/namel3ss/studio/web/index.html").read_text(encoding="utf-8")
    assert 'data-testid="studio-topbar"' in html
    assert 'data-testid="studio-dock"' in html
    dock_items = re.findall(r'data-testid="studio-dock-item-[^"]+"', html)
    assert len(dock_items) == 11
