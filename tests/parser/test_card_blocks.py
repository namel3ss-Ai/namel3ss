import pytest

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from tests.conftest import parse_program


def test_parse_card_group_and_blocks():
    source = '''flow "go":
  return "ok"

page "home":
  card_group:
    card "Summary":
      stat:
        value is state.total
        label is "Total"
      actions:
        action "Run":
          calls flow "go"
      text is "Done"
    card:
      text is "Second"
'''
    program = parse_program(source)
    page = program.pages[0]
    group = page.items[0]
    assert isinstance(group, ast.CardGroupItem)
    assert len(group.children) == 2
    card = group.children[0]
    assert isinstance(card, ast.CardItem)
    assert card.label == "Summary"
    assert isinstance(card.stat, ast.CardStat)
    assert card.stat.label == "Total"
    assert isinstance(card.stat.value, ast.StatePath)
    assert card.actions and isinstance(card.actions[0], ast.CardAction)


def test_card_group_rejects_non_cards():
    source = '''page "home":
  card_group:
    text is "Not allowed"
'''
    with pytest.raises(Namel3ssError) as err:
        parse_program(source)
    assert "card groups may only contain cards" in str(err.value).lower()


def test_card_stat_requires_value():
    source = '''page "home":
  card "Summary":
    stat:
      label is "Total"
'''
    with pytest.raises(Namel3ssError) as err:
        parse_program(source)
    assert "stat block requires value" in str(err.value).lower()


def test_card_stat_duplicate_block():
    source = '''page "home":
  card "Summary":
    stat:
      value is 1
    stat:
      value is 2
'''
    with pytest.raises(Namel3ssError) as err:
        parse_program(source)
    assert "stat block is declared more than once" in str(err.value).lower()


def test_card_actions_require_entries():
    source = '''page "home":
  card "Summary":
    actions:
'''
    with pytest.raises(Namel3ssError) as err:
        parse_program(source)
    assert "actions block has no entries" in str(err.value).lower()
