from pathlib import Path
import shutil
import pytest

from namel3ss.config.loader import load_config
from namel3ss.module_loader import load_project
from namel3ss.cli.build_mode import run_build_command
from namel3ss.cli.builds import read_latest_build_id
from namel3ss.cli.targets_store import build_dir
from namel3ss.runtime.identity.context import resolve_identity
from namel3ss.ui.manifest import build_manifest
from namel3ss.validation import ValidationMode, ValidationWarning


TEMPLATE_APPS = sorted(Path("src/namel3ss/templates").glob("*/app.ai"))


def _assert_static_builds(app_path: Path) -> dict:
    project = load_project(app_path)
    program = project.program
    config = load_config(app_path=app_path)
    warnings: list[ValidationWarning] = []
    identity = resolve_identity(
        config,
        getattr(program, "identity", None),
        mode=ValidationMode.STATIC,
        warnings=warnings,
    )
    manifest = build_manifest(
        program,
        state={},
        identity=identity,
        mode=ValidationMode.STATIC,
        warnings=warnings,
    )
    assert isinstance(manifest, dict)
    assert "pages" in manifest
    return manifest


@pytest.mark.parametrize("app_path", TEMPLATE_APPS, ids=lambda p: f"template-{p.parent.name}")
def test_templates_build_in_static_mode(app_path: Path) -> None:
    manifest = _assert_static_builds(app_path)
    assert manifest.get("pages")
    assert manifest.get("actions")


@pytest.mark.parametrize("app_path", TEMPLATE_APPS, ids=lambda p: f"template-build-{p.parent.name}")
def test_templates_build_in_pack_mode(tmp_path: Path, app_path: Path) -> None:
    template_root = app_path.parent
    dest_root = tmp_path / template_root.name
    shutil.copytree(template_root, dest_root)
    built_app = dest_root / "app.ai"
    assert run_build_command([built_app.as_posix(), "--target", "service"]) == 0
    build_id = read_latest_build_id(dest_root, "service")
    assert build_id
    build_path = build_dir(dest_root, "service", build_id)
    assert (build_path / "build.json").exists()
    assert (build_path / "manifest.json").exists()
