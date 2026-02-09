from namel3ss.determinism import canonical_json_dumps
from namel3ss.ui.manifest import build_manifest
from tests.conftest import lower_ir_program

SOURCE = '''spec is "1.0"

capabilities:
  ui_theme

page "Theme":
  tokens:
    size is "compact"
    radius is "md"
    density is "regular"
    font is "sm"
    color_scheme is "dark"

  card "Panel":
    size is "comfortable"
    text is "Hello"

  include theme_settings_page
'''

STATE = {
    "ui": {
        "settings": {
            "size": "normal",
            "radius": "lg",
        }
    }
}


def test_ui_theme_manifest_determinism() -> None:
    program = lower_ir_program(SOURCE)
    first = build_manifest(program, state=dict(STATE), store=None)
    second = build_manifest(program, state=dict(STATE), store=None)
    assert canonical_json_dumps(first, pretty=False) == canonical_json_dumps(second, pretty=False)
