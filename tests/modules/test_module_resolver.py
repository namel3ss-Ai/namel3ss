from pathlib import Path

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.modules.resolver import resolve_module_path


def test_resolve_module_path_normalizes(tmp_path: Path) -> None:
    module_path = tmp_path / "modules" / "common.ai"
    module_path.parent.mkdir(parents=True, exist_ok=True)
    module_path.write_text("", encoding="utf-8")
    resolved = resolve_module_path(tmp_path, "modules/common.ai")
    assert resolved == module_path.resolve()
    resolved_backslash = resolve_module_path(tmp_path, "modules\\common.ai")
    assert resolved_backslash == module_path.resolve()


def test_resolve_module_path_rejects_absolute(tmp_path: Path) -> None:
    module_path = tmp_path / "modules" / "abs.ai"
    with pytest.raises(Namel3ssError):
        resolve_module_path(tmp_path, module_path.as_posix())


def test_resolve_module_path_rejects_traversal(tmp_path: Path) -> None:
    with pytest.raises(Namel3ssError):
        resolve_module_path(tmp_path, "../outside.ai")


def test_resolve_module_path_rejects_extension(tmp_path: Path) -> None:
    with pytest.raises(Namel3ssError):
        resolve_module_path(tmp_path, "modules/common.txt")
