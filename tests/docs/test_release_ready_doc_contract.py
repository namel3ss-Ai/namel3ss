from pathlib import Path


def test_release_ready_doc_contract() -> None:
    text = Path("docs/release-ready.md").read_text(encoding="utf-8")
    required = [
        "What release-ready means",
        "How to run full release checks locally",
        "Guarantees",
        "Not guaranteed",
        "Reference apps",
        "python3 -m pytest -q",
        "n3 release-check",
        "repo_clean",
    ]
    for item in required:
        assert item in text, f"Missing '{item}' in docs/release-ready.md"
