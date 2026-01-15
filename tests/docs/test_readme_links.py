from pathlib import Path


def test_readme_links_present():
    readme = Path("README.md").read_text(encoding="utf-8")
    required_links = [
        "docs/quickstart.md",
        "docs/first-5-minutes.md",
        "docs/what-you-can-build-today.md",
        "docs/stability.md",
        "resources/limitations.md",
    ]
    for link in required_links:
        assert link in readme
    assert "Try it in 60 seconds" in readme
