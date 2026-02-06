from pathlib import Path


def test_dependency_management_doc_exists_and_mentions_core_contracts() -> None:
    path = Path("docs/dependency-management.md")
    assert path.exists(), "docs/dependency-management.md missing"
    text = path.read_text(encoding="utf-8")
    for token in [
        "dependency_management",
        "namel3ss.toml",
        "namel3ss.lock",
        "[runtime.dependencies]",
        "n3 install",
        "n3 deps add",
        "n3 deps audit",
    ]:
        assert token in text
