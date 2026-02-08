from __future__ import annotations

from pathlib import Path


def test_trust_doc_mentions_deterministic_artifacts() -> None:
    root = Path(__file__).resolve().parents[2]
    doc_path = root / "docs" / "trust-and-governance.md"
    text = doc_path.read_text(encoding="utf-8")
    assert "canonicalized without timestamps" in text
    assert "n3 status" in text and "n3 explain" in text and "n3 clean" in text
