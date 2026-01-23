from pathlib import Path


def test_quickstart_scaffold_contract() -> None:
    text = Path("docs/quickstart.md").read_text(encoding="utf-8")
    required = [
        "Scaffolded app structure",
        "expected_ui.json",
        ".gitignore",
        "Examples (read-only)",
        "n3 new example",
    ]
    for item in required:
        assert item in text, f"Missing '{item}' in docs/quickstart.md"


def test_upgrade_doc_contract() -> None:
    text = Path("UPGRADE.md").read_text(encoding="utf-8")
    required = [
        "Breaking changes",
        "How to detect breaking changes",
        "How to fix or migrate manually",
        "n3 app.ai check",
    ]
    for item in required:
        assert item in text, f"Missing '{item}' in UPGRADE.md"
