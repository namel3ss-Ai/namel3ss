from pathlib import Path


TEMPLATE_ROOT = Path("src/namel3ss/templates")
EXPECTED_TEMPLATES = {"composition", "operations_dashboard", "onboarding", "support_inbox"}
ROOT_AI_ALLOWLIST: set[str] = set()


def _template_dirs() -> list[Path]:
    return sorted(
        [
            path
            for path in TEMPLATE_ROOT.iterdir()
            if path.is_dir() and (path / "app.ai").exists()
        ],
        key=lambda p: p.name,
    )


def test_templates_have_required_layout() -> None:
    templates = _template_dirs()
    assert templates
    assert {template.name for template in templates} == EXPECTED_TEMPLATES
    assert not (TEMPLATE_ROOT / "starter").exists()
    assert not (TEMPLATE_ROOT / "demo").exists()
    for template in templates:
        assert (template / "app.ai").exists()
        assert (template / "README.md").exists()
        assert (template / "expected_ui.json").exists()
        assert (template / ".gitignore").exists()


def test_root_ai_files_are_whitelisted() -> None:
    root_ai_files = sorted(path.name for path in Path(".").glob("*.ai"))
    unexpected = [name for name in root_ai_files if name not in ROOT_AI_ALLOWLIST]
    assert unexpected == []
