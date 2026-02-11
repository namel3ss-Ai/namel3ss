from __future__ import annotations

import pytest

from namel3ss.cli.project_discovery import discover_compile_app_path
from namel3ss.errors.base import Namel3ssError


def test_discover_compile_app_path_accepts_project_directory(tmp_path) -> None:
    project = tmp_path / "proj"
    project.mkdir()
    app = project / "app.ai"
    app.write_text('spec is "1.0"\n\nflow "demo":\n  return "ok"\n', encoding="utf-8")
    resolved = discover_compile_app_path(project.as_posix())
    assert resolved == app.resolve()


def test_discover_compile_app_path_requires_canonical_app_file(tmp_path) -> None:
    project = tmp_path / "proj"
    project.mkdir()
    with pytest.raises(Namel3ssError) as err:
        discover_compile_app_path(project.as_posix())
    assert 'Project root is missing "app.ai".' in str(err.value)
