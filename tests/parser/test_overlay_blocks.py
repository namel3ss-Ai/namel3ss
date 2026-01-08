import pytest

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from tests.conftest import parse_program


def test_parse_modal_and_drawer_blocks():
    source = '''page "home":
  modal "Confirm":
    text is "Sure"
  drawer "Details":
    text is "More"
'''
    program = parse_program(source)
    items = program.pages[0].items
    assert isinstance(items[0], ast.ModalItem)
    assert items[0].label == "Confirm"
    assert isinstance(items[1], ast.DrawerItem)
    assert items[1].label == "Details"


def test_parse_action_opens_modal():
    source = '''page "home":
  modal "Confirm":
    text is "Sure"
  card "Actions":
    actions:
      action "Open":
        opens modal "Confirm"
'''
    program = parse_program(source)
    card = next(item for item in program.pages[0].items if isinstance(item, ast.CardItem))
    action = card.actions[0]
    assert action.kind == "open_modal"
    assert action.target == "Confirm"


def test_nested_modal_rejected():
    source = '''page "home":
  section:
    modal "Confirm":
      text is "Nope"
'''
    with pytest.raises(Namel3ssError) as exc:
        parse_program(source)
    assert "page root" in str(exc.value).lower()


def test_action_requires_modal_or_drawer_target():
    source = '''page "home":
  card "Actions":
    actions:
      action "Open":
        opens sheet "Confirm"
'''
    with pytest.raises(Namel3ssError) as exc:
        parse_program(source)
    assert "modal or drawer" in str(exc.value).lower()
