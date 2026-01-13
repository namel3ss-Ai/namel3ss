from pathlib import Path

import pytest

from namel3ss.config.loader import load_config
from namel3ss.module_loader import load_project
from namel3ss.runtime.identity.context import resolve_identity
from namel3ss.ui.manifest import build_manifest
from namel3ss.validation import ValidationMode, ValidationWarning


TEMPLATE_APPS = sorted(Path("src/namel3ss/templates").glob("*/app.ai"))
EXAMPLE_APPS = sorted(
    path
    for path in Path("examples").glob("**/*.ai")
    if "modules" not in path.parts and "packages" not in path.parts and "tests" not in path.parts
)


def _assert_static_builds(app_path: Path) -> None:
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


@pytest.mark.parametrize("app_path", TEMPLATE_APPS, ids=lambda p: f"template-{p.parent.name}")
def test_templates_build_in_static_mode(app_path: Path) -> None:
    _assert_static_builds(app_path)


@pytest.mark.parametrize("app_path", EXAMPLE_APPS, ids=lambda p: f"example-{p.relative_to(Path('examples'))}")
def test_examples_build_in_static_mode(app_path: Path) -> None:
    _assert_static_builds(app_path)
