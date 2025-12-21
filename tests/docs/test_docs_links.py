from pathlib import Path


def test_readme_links_present():
    text = Path("README.md").read_text(encoding="utf-8")
    for target in [
        "docs/quickstart.md",
        "docs/first-5-minutes.md",
        "docs/what-you-can-build-today.md",
        "docs/stability.md",
    ]:
        assert target in text


def test_docs_files_exist_and_not_empty():
    for path in [
        Path("docs/quickstart.md"),
        Path("docs/first-5-minutes.md"),
        Path("docs/what-you-can-build-today.md"),
        Path("docs/stability.md"),
    ]:
        assert path.exists()
        assert path.read_text(encoding="utf-8").strip() != ""
