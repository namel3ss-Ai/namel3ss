from __future__ import annotations

import pytest

from namel3ss.cli.build_mode import run_build_command
from namel3ss.errors.base import Namel3ssError


BASE_SOURCE = '''spec is "1.0"

record "Note":
  title text

flow "demo":
  return "ok"
'''

CHANGED_SOURCE = '''spec is "1.0"

record "Note":
  title number

flow "demo":
  return "ok"
'''


def test_build_blocks_breaking_schema(tmp_path) -> None:
    app_path = tmp_path / "app.ai"
    app_path.write_text(BASE_SOURCE, encoding="utf-8")
    assert run_build_command([app_path.as_posix(), "--target", "local"]) == 0

    app_path.write_text(CHANGED_SOURCE, encoding="utf-8")
    with pytest.raises(Namel3ssError) as exc:
        run_build_command([app_path.as_posix(), "--target", "local"])
    assert "schema" in str(exc.value).lower()
