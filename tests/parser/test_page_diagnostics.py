import pytest

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from tests.conftest import parse_program


def test_parse_page_diagnostics_metadata_and_layout_block():
    source = '''page "Chat":
  diagnostics is true
  layout:
    main:
      title is "Chat"
    diagnostics:
      section "Trace":
        text is "Details"
'''
    page = parse_program(source).pages[0]
    assert page.diagnostics is True
    assert isinstance(page.layout, ast.PageLayout)
    assert len(page.layout.main) == 1
    assert len(page.layout.diagnostics) == 1
    assert isinstance(page.layout.diagnostics[0], ast.SectionItem)
    assert len(page.items) == 1


def test_page_layout_rejects_duplicate_diagnostics_block():
    source = '''page "Chat":
  layout:
    main:
      title is "Chat"
    diagnostics:
      text is "one"
    diagnostics:
      text is "two"
'''
    with pytest.raises(Namel3ssError) as exc:
        parse_program(source)
    assert "already declared" in str(exc.value).lower()


def test_page_rejects_duplicate_diagnostics_metadata():
    source = '''page "Chat":
  diagnostics is true
  diagnostics is false
  title is "Chat"
'''
    with pytest.raises(Namel3ssError) as exc:
        parse_program(source)
    assert "diagnostics is already declared" in str(exc.value)


def test_diagnostics_metadata_requires_boolean_literal():
    source = '''page "Chat":
  diagnostics is "true"
  title is "Chat"
'''
    with pytest.raises(Namel3ssError) as exc:
        parse_program(source)
    assert "diagnostics must be a boolean literal" in str(exc.value)
