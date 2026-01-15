from pathlib import Path
import json
import pytest

from namel3ss.config.loader import load_config
from namel3ss.module_loader import load_project
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
    stored_path = app_path.parent / "manifest" / "ui.json"
    assert stored_path.exists()
    stored = json.loads(stored_path.read_text(encoding="utf-8"))
    assert stored == manifest
