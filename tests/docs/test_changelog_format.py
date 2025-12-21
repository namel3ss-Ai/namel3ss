from pathlib import Path


def test_changelog_has_required_sections():
    changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")
    required = ["Added", "Changed", "Fixed", "Deprecated", "Removed"]
    for header in required:
        assert header in changelog
    assert "No breaking changes without an explicit changelog entry." in changelog
