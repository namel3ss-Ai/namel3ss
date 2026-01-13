from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "docs" / "language" / "grammar_contract.md"
SNAPSHOT = ROOT / "docs" / "grammar" / "current.md"
GRAMMAR_TEST = ROOT / "tests" / "parser" / "test_grammar_current.py"


def test_contract_doc_is_present_and_bannered() -> None:
    assert CONTRACT.exists(), "grammar_contract.md must exist"
    text = CONTRACT.read_text(encoding="utf-8")
    assert "This document defines the frozen grammar and semantics of namel3ss." in text
    assert "Changes require explicit compatibility review." in text


def test_snapshot_doc_is_not_treated_as_contract() -> None:
    assert SNAPSHOT.exists(), "Snapshot doc must remain for historical reference"
    text = SNAPSHOT.read_text(encoding="utf-8").lower()
    assert "snapshot" in text
    assert "not the authoritative contract" in text


def test_grammar_contract_tests_are_present() -> None:
    assert GRAMMAR_TEST.exists(), "Grammar contract tests must remain in the suite"
