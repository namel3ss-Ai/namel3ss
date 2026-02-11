from __future__ import annotations

import pytest

from namel3ss.errors.base import Namel3ssError
from tests.conftest import lower_ir_program


_MISSING_SLIDER_CAP = (
    "Capability missing: ui.slider is required to use 'slider' controls. "
    "Add 'capability is ui.slider' to the manifest."
)
_MISSING_TOOLTIP_CAP = (
    "Capability missing: ui.tooltip is required to use 'tooltip' components. "
    "Add 'capability is ui.tooltip' to the manifest."
)


def test_slider_requires_ui_slider_capability() -> None:
    source = '''
spec is "1.0"

flow "set_semantic_weight":
  return "ok"

page "home":
  slider "Semantic weight":
    min is 0
    max is 1
    step is 0.1
    value is state.retrieval.semantic_weight
    on change run "set_semantic_weight"
'''.lstrip()
    with pytest.raises(Namel3ssError) as err:
        lower_ir_program(source)
    assert _MISSING_SLIDER_CAP in str(err.value)


def test_slider_range_validation() -> None:
    source = '''
spec is "1.0"

capabilities:
  ui.slider

flow "set_semantic_weight":
  return "ok"

page "home":
  slider "Semantic weight":
    min is 1
    max is 1
    step is 0.1
    value is state.retrieval.semantic_weight
    on change run "set_semantic_weight"
'''.lstrip()
    with pytest.raises(Namel3ssError) as err:
        lower_ir_program(source)
    assert "requires min < max" in str(err.value)


def test_slider_step_validation() -> None:
    source = '''
spec is "1.0"

capabilities:
  ui.slider

flow "set_semantic_weight":
  return "ok"

page "home":
  slider "Semantic weight":
    min is 0
    max is 1
    step is 0
    value is state.retrieval.semantic_weight
    on change run "set_semantic_weight"
'''.lstrip()
    with pytest.raises(Namel3ssError) as err:
        lower_ir_program(source)
    assert "requires step > 0" in str(err.value)


def test_duplicate_slider_labels_in_same_container() -> None:
    source = '''
spec is "1.0"

capabilities:
  ui.slider

flow "set_semantic_weight":
  return "ok"

page "home":
  slider "Semantic weight":
    min is 0
    max is 1
    step is 0.1
    value is state.retrieval.semantic_weight
    on change run "set_semantic_weight"
  slider "Semantic weight":
    min is 0
    max is 1
    step is 0.1
    value is state.retrieval.semantic_weight
    on change run "set_semantic_weight"
'''.lstrip()
    with pytest.raises(Namel3ssError) as err:
        lower_ir_program(source)
    assert "Duplicate control label 'Semantic weight'" in str(err.value)


def test_tooltip_requires_ui_tooltip_capability() -> None:
    source = '''
spec is "1.0"

capabilities:
  ui.slider

flow "set_semantic_weight":
  return "ok"

page "home":
  slider "Semantic weight":
    min is 0
    max is 1
    step is 0.1
    value is state.retrieval.semantic_weight
    on change run "set_semantic_weight"
    help is "Blend semantic and lexical retrieval."
'''.lstrip()
    with pytest.raises(Namel3ssError) as err:
        lower_ir_program(source)
    assert _MISSING_TOOLTIP_CAP in str(err.value)


def test_duplicate_tooltip_anchor_is_error() -> None:
    source = '''
spec is "1.0"

capabilities:
  ui.slider
  ui.tooltip

flow "set_semantic_weight":
  return "ok"

page "home":
  slider "Semantic weight":
    min is 0
    max is 1
    step is 0.1
    value is state.retrieval.semantic_weight
    on change run "set_semantic_weight"
    help is "Blend semantic and lexical retrieval."
  tooltip "Another tip" for "Semantic weight"
'''.lstrip()
    with pytest.raises(Namel3ssError) as err:
        lower_ir_program(source)
    assert "Duplicate tooltips attached to control 'Semantic weight'." in str(err.value)

