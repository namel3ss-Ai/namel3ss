from pathlib import Path
import shutil

from namel3ss.cli.build_mode import run_build_command
from namel3ss.cli.builds import read_latest_build_id
from namel3ss.cli.check_mode import run_check
from namel3ss.cli.targets_store import build_dir
from namel3ss.module_loader import load_project
from namel3ss.ui.manifest import build_manifest
from namel3ss.validation import ValidationMode, ValidationWarning

REFERENCE_APPS = [
    Path("evals/apps/reference_release_hub/app.ai"),
]


def _copy_app(app_path: Path, tmp_path: Path) -> Path:
    root = app_path.parent
    dest_root = tmp_path / root.name
    shutil.copytree(root, dest_root)
    return dest_root / app_path.name


def test_reference_apps_are_read_only() -> None:
    for app_path in REFERENCE_APPS:
        readme = app_path.parent / "README.md"
        assert readme.exists(), f"Missing README for {app_path.parent}"
        text = readme.read_text(encoding="utf-8")
        assert "read-only" in text.lower()


def test_reference_apps_check_and_manifest(tmp_path: Path) -> None:
    for app_path in REFERENCE_APPS:
        copied_app = _copy_app(app_path, tmp_path)
        assert run_check(copied_app.as_posix()) == 0
        project = load_project(copied_app)
        warnings: list[ValidationWarning] = []
        manifest = build_manifest(
            project.program,
            state={},
            store=None,
            mode=ValidationMode.STATIC,
            warnings=warnings,
        )
        codes = sorted({warn.code for warn in warnings})
        assert "requires.skipped" in codes
        assert manifest.get("pages")
        assert manifest.get("actions") is not None


def test_reference_apps_build(tmp_path: Path) -> None:
    for app_path in REFERENCE_APPS:
        copied_app = _copy_app(app_path, tmp_path)
        assert run_build_command([copied_app.as_posix(), "--target", "service"]) == 0
        build_id = read_latest_build_id(copied_app.parent, "service")
        assert build_id
        build_path = build_dir(copied_app.parent, "service", build_id)
        assert (build_path / "build.json").exists()
        assert (build_path / "manifest.json").exists()
