from pathlib import Path


def test_streaming_doc_exists_and_contains_core_contracts() -> None:
    path = Path("docs/streaming.md")
    assert path.exists(), "docs/streaming.md missing"
    text = path.read_text(encoding="utf-8")
    for required in [
        "streaming",
        "stream: true",
        "Determinism",
        "Error behaviour",
        "/api/action/stream",
    ]:
        assert required in text
