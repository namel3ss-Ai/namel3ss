from pathlib import Path

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.studio.server import require_app_path


def test_require_app_path_missing():
    with pytest.raises(Namel3ssError) as excinfo:
        require_app_path(None)
    assert "Studio needs an app file path" in str(excinfo.value)


def test_require_app_path_resolves(tmp_path: Path):
    app_file = tmp_path / "app.ai"
    app_file.write_text('spec is "1.0"\n\nflow "demo":\n  return "ok"\n', encoding="utf-8")
    resolved = require_app_path(app_file)
    assert resolved == app_file.resolve()
