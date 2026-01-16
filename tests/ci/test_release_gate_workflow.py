from pathlib import Path


def test_release_gate_workflow_has_full_suite_and_clean_check() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    required = [
        "release-gate",
        "python -m pytest -q",
        "tests/runtime/test_production_server.py",
        "tools/clean_pattern_artifacts.py",
        "repo_clean",
    ]
    for item in required:
        assert item in workflow, f"Missing '{item}' in .github/workflows/ci.yml"
