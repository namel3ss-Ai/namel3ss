from pathlib import Path


def test_dev_preview_docs_contract() -> None:
    text = Path("docs/runtime.md").read_text(encoding="utf-8")
    required = [
        "n3 dev",
        "n3 preview",
        "hot reload",
        "never render a blank screen",
        "overlay",
        "Recovery is automatic",
    ]
    for item in required:
        assert item in text, f"Missing '{item}' in docs/runtime.md"
