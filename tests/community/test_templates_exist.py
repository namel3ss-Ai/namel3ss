from pathlib import Path


REQUIRED = [
    ".github/ISSUE_TEMPLATE/bug_report.md",
    ".github/ISSUE_TEMPLATE/feature_request.md",
    ".github/ISSUE_TEMPLATE/design_feedback.md",
    ".github/DISCUSSION_TEMPLATE/show-and-tell.md",
    ".github/DISCUSSION_TEMPLATE/design-discussion.md",
    ".github/DISCUSSION_TEMPLATE/help-qa.md",
]


def test_templates_exist_and_non_empty():
    for rel in REQUIRED:
        path = Path(rel)
        assert path.exists(), f"{rel} missing"
        assert path.read_text(encoding="utf-8").strip(), f"{rel} is empty"
