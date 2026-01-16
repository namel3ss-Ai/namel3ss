from pathlib import Path


def test_studio_doc_parity_section() -> None:
    text = Path("docs/studio.md").read_text(encoding="utf-8")
    assert "inspection lens" in text.lower()
    assert "CLI parity" in text
    assert "n3 ui --json" in text
    assert "n3 check" in text
    assert "n3 explain --json" in text
    assert "n3 actions --json" in text
