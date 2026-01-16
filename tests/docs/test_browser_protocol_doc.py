from pathlib import Path


DOC_PATH = Path("docs/runtime/browser-protocol.md")


def test_browser_protocol_doc_exists() -> None:
    assert DOC_PATH.exists()
    text = DOC_PATH.read_text(encoding="utf-8")
    assert text.strip()
    assert "Browser Protocol" in text.splitlines()[0]
    assert "v1" not in text.splitlines()[0].lower()
    for token in ["/api/ui", "/api/state", "/api/action", "/api/health", "deterministic"]:
        assert token in text


def test_browser_protocol_links_present() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    assert str(DOC_PATH) in readme
    assert "Browser Protocol" in readme
    learning = Path("docs/learning-namel3ss.md").read_text(encoding="utf-8")
    assert "runtime/browser-protocol.md" in learning
    assert "Browser Protocol" in learning
    lang_def = Path("docs/ai-language-definition.md").read_text(encoding="utf-8")
    assert "runtime/browser-protocol.md" in lang_def
    assert "Browser Protocol" in lang_def
