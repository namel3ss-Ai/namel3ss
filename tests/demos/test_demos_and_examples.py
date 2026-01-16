from pathlib import Path

from namel3ss.cli.main import main


DEMOS_ROOT = Path("src/namel3ss/demos")
EXAMPLES_ROOT = Path("src/namel3ss/examples")


def _ai_paths(root: Path) -> list[Path]:
    return sorted(root.glob("*/app.ai"))


def test_demos_have_required_layout() -> None:
    demo_apps = _ai_paths(DEMOS_ROOT)
    assert demo_apps, "No demos found"
    for app_path in demo_apps:
        assert (app_path.parent / "README.md").exists()


def test_smoke_demo_validates() -> None:
    smoke_app = DEMOS_ROOT / "smoke" / "app.ai"
    assert smoke_app.exists()
    assert main([smoke_app.as_posix(), "check"]) == 0


def test_examples_are_single_concept_and_validate() -> None:
    example_apps = _ai_paths(EXAMPLES_ROOT)
    assert example_apps, "No examples found"
    for app_path in example_apps:
        root = app_path.parent
        files = [p for p in root.rglob("*") if p.is_file()]
        allowed = {"app.ai", "README.md"}
        for path in files:
            rel = path.relative_to(root)
            if rel.parts[0].startswith("__pycache__"):
                continue
            assert rel.as_posix() in allowed
        assert main([app_path.as_posix(), "check"]) == 0
