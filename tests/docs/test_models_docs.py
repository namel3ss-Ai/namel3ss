from pathlib import Path


def test_models_docs_exist_and_are_short():
    required = {
        "engine.md",
        "capsule.md",
        "package.md",
        "proof.md",
        "verify.md",
        "secrets.md",
        "observe.md",
        "identity.md",
    }
    docs_dir = Path("docs/models")
    assert docs_dir.exists()
    found = {path.name for path in docs_dir.glob("*.md")}
    assert required.issubset(found)
    for name in required:
        path = docs_dir / name
        text = path.read_text(encoding="utf-8").strip()
        assert text
        assert "```" in text
        assert "n3 " in text
        assert len(text.splitlines()) <= 60


def test_learning_overlay_links_resolve():
    overlay_path = Path("src/namel3ss/studio/web/learning_overlay.json")
    data = overlay_path.read_text(encoding="utf-8")
    import json

    payload = json.loads(data)
    for item in payload.get("items", []):
        doc = item.get("doc")
        assert doc, "Overlay items must include doc links"
        doc_path = Path(doc)
        assert doc_path.exists(), f"Missing doc target: {doc_path}"
