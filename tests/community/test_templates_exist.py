from pathlib import Path


REQUIRED = [
    ".github/ISSUE_TEMPLATE/config.yml",
    ".github/ISSUE_TEMPLATE/bug.yml",
    ".github/ISSUE_TEMPLATE/docs.yml",
    ".github/ISSUE_TEMPLATE/tests.yml",
    ".github/ISSUE_TEMPLATE/dx.yml",
    ".github/DISCUSSION_TEMPLATE/show-and-tell.md",
    ".github/DISCUSSION_TEMPLATE/design-discussion.md",
    ".github/DISCUSSION_TEMPLATE/help-qa.md",
]


def test_templates_exist_and_non_empty():
    for rel in REQUIRED:
        path = Path(rel)
        assert path.exists(), f"{rel} missing"
        assert path.read_text(encoding="utf-8").strip(), f"{rel} is empty"
