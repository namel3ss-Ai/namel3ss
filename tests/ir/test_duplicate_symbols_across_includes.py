from __future__ import annotations

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.module_loader import load_project


def test_duplicate_flow_name_across_includes_is_hard_error(tmp_path) -> None:
    root = tmp_path
    app = root / "app.ai"
    first = root / "modules" / "one.ai"
    second = root / "modules" / "two.ai"
    first.parent.mkdir(parents=True, exist_ok=True)

    app.write_text(
        """
spec is "1.0"

capabilities:
  composition.includes

include "modules/one.ai"
include "modules/two.ai"

flow "root_main":
  return "ok"
""".lstrip(),
        encoding="utf-8",
    )
    first.write_text(
        """
flow "shared":
  return "one"
""".lstrip(),
        encoding="utf-8",
    )
    second.write_text(
        """
flow "shared":
  return "two"
""".lstrip(),
        encoding="utf-8",
    )

    with pytest.raises(Namel3ssError) as err:
        load_project(app)
    assert str(err.value) == (
        'Compile error: duplicate declaration \'shared\' found in "modules/two.ai" '
        '(already defined in "modules/one.ai")'
    )
