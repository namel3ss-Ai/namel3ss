from namel3ss.determinism import canonical_json_dumps
from namel3ss.ui.manifest import build_manifest
from tests.conftest import lower_ir_program

SOURCE = '''spec is "1.0"

capabilities:
  ui_layout

page "Deterministic Layout":
  stack:
    text is "One" show_when is state.show
    row:
      col:
        text is "Left"
      col:
        text is "Right"
    if state.toggle:
      text is "On"
    else:
      text is "Off"
  sticky top:
    text is "Sticky"
'''

STATE = {
    "show": True,
    "toggle": False,
}


def test_ui_layout_manifest_determinism() -> None:
    program = lower_ir_program(SOURCE)
    first = build_manifest(program, state=dict(STATE), store=None)
    second = build_manifest(program, state=dict(STATE), store=None)
    assert canonical_json_dumps(first, pretty=False) == canonical_json_dumps(second, pretty=False)

