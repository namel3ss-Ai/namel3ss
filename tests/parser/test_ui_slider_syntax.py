from __future__ import annotations

import pytest

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from tests.conftest import parse_program


def test_parse_slider_item_with_help() -> None:
    source = '''
page "home":
  slider "Semantic weight":
    min is 0
    max is 1
    step is 0.05
    value is state.retrieval.semantic_weight
    on change run "set_semantic_weight"
    help is "Controls semantic-vs-lexical blending."
'''.lstrip()
    program = parse_program(source)
    slider = next(item for item in program.pages[0].items if isinstance(item, ast.SliderItem))
    assert slider.label == "Semantic weight"
    assert slider.min_value == 0.0
    assert slider.max_value == 1.0
    assert slider.step == 0.05
    assert slider.value.path == ["retrieval", "semantic_weight"]
    assert slider.flow_name == "set_semantic_weight"
    assert slider.help_text == "Controls semantic-vs-lexical blending."


def test_slider_missing_required_fields_is_parse_error() -> None:
    source = '''
page "home":
  slider "Semantic weight":
    min is 0
    max is 1
    value is state.retrieval.semantic_weight
'''.lstrip()
    with pytest.raises(Namel3ssError) as err:
        parse_program(source)
    assert "slider requires 'min', 'max', 'step', 'value', and 'on change'." in str(err.value)


def test_slider_rejects_non_state_value_binding() -> None:
    source = '''
page "home":
  slider "Semantic weight":
    min is 0
    max is 1
    step is 0.1
    value is "bad"
    on change run "set_semantic_weight"
'''.lstrip()
    with pytest.raises(Namel3ssError):
        parse_program(source)

