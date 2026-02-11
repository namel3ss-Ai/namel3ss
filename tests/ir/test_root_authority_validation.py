from __future__ import annotations

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.module_loader import load_project


def test_included_file_cannot_define_pages_or_ui(tmp_path) -> None:
    root = tmp_path
    app = root / "app.ai"
    module_page = root / "modules" / "page_defs.ai"
    module_page.parent.mkdir(parents=True, exist_ok=True)
    app.write_text(
        """
spec is "1.0"

capabilities:
  composition.includes

include "modules/page_defs.ai"

page "home":
  title is "Root"
""".lstrip(),
        encoding="utf-8",
    )
    module_page.write_text(
        """
page "illegal":
  title is "Not allowed"
""".lstrip(),
        encoding="utf-8",
    )

    with pytest.raises(Namel3ssError) as err:
        load_project(app)
    assert str(err.value) == 'Compile error: only the root file may define \'ui\' and \'pages\'. Found in "modules/page_defs.ai"'
