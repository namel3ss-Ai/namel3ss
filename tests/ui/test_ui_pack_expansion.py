import pytest

from namel3ss.errors.base import Namel3ssError
from tests.conftest import lower_ir_program


def test_ui_pack_unknown_pack_errors():
    source = '''page "home":
  use ui_pack "missing" fragment "summary"
'''
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "unknown ui_pack" in str(exc.value).lower()


def test_ui_pack_missing_fragment_errors():
    source = '''ui_pack "widgets":
  version is "1"
  fragment "summary":
    text is "Hi"

page "home":
  use ui_pack "widgets" fragment "missing"
'''
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "no fragment" in str(exc.value).lower()


def test_ui_pack_cycle_errors():
    source = '''ui_pack "widgets":
  version is "1"
  fragment "loop":
    use ui_pack "widgets" fragment "loop"

page "home":
  use ui_pack "widgets" fragment "loop"
'''
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "cycle" in str(exc.value).lower()


def test_ui_pack_tabs_disallowed_outside_page_root():
    source = '''ui_pack "widgets":
  version is "1"
  fragment "tabbed":
    tabs:
      tab "One":
        text is "Hi"

page "home":
  section:
    use ui_pack "widgets" fragment "tabbed"
'''
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "page root" in str(exc.value).lower()


def test_ui_pack_rows_require_columns():
    source = '''ui_pack "widgets":
  version is "1"
  fragment "snippet":
    text is "Hi"

page "home":
  row:
    use ui_pack "widgets" fragment "snippet"
'''
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "ui layout requires capability ui_layout" in str(exc.value).lower()
