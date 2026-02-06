from pathlib import Path


def test_multimodal_doc_exists_and_has_core_sections():
    path = Path("docs/multimodal.md")
    assert path.exists(), "docs/multimodal.md missing"
    text = path.read_text(encoding="utf-8")
    for required in [
        "mode: image",
        "mode: audio",
        "capabilities:",
        "vision",
        "speech",
        "Determinism",
        "Error behaviour",
    ]:
        assert required in text
