from pathlib import Path

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.module_loader import load_project


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_module_rejects_flows(tmp_path: Path) -> None:
    app_path = tmp_path / "app.ai"
    module_path = tmp_path / "modules" / "bad.ai"
    _write(
        module_path,
        (
            'flow "demo":\n'
            '  return "ok"\n'
        ),
    )
    _write(
        app_path,
        (
            'spec is "1.0"\n\n'
            'use module "modules/bad.ai" as bad\n\n'
            'flow "run":\n'
            '  return "ok"\n'
        ),
    )
    with pytest.raises(Namel3ssError):
        load_project(app_path)


def test_module_rejects_use_module(tmp_path: Path) -> None:
    app_path = tmp_path / "app.ai"
    module_path = tmp_path / "modules" / "bad.ai"
    _write(
        module_path,
        (
            'use module "modules/other.ai" as other\n\n'
            'define function "value":\n'
            '  input:\n'
            '    x is number\n'
            '  return 1\n'
        ),
    )
    _write(
        app_path,
        (
            'spec is "1.0"\n\n'
            'use module "modules/bad.ai" as bad\n\n'
            'flow "run":\n'
            '  return "ok"\n'
        ),
    )
    with pytest.raises(Namel3ssError):
        load_project(app_path)
