import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.studio.edit.ops import apply_edit_to_source
from namel3ss.studio.session import SessionState
from namel3ss.ui.manifest import build_manifest
from tests.conftest import lower_ir_program


def _manifest(source):
    program = lower_ir_program(source)
    return build_manifest(program, state={}, store=None)


def test_insert_text_into_root():
    source = '''flow "go":
  return "ok"

page "home":
  title is "Welcome"
'''
    manifest = _manifest(source)
    target = manifest["pages"][0]["elements"][0]
    updated, ir, manifest_out = apply_edit_to_source(
        source,
        "insert",
        {"page": "home", "element_id": target["element_id"], "position": "after"},
        {"type": "text", "value": "Hello"},
        SessionState(),
    )
    assert "text is \"Hello\"" in updated
    assert any(el["type"] == "text" for el in manifest_out["pages"][0]["elements"])
    # round-trip still parses/lowers
    assert ir.pages[0].name == "home"


def test_insert_into_row_requires_column():
    source = '''page "home":
  row:
    column:
      text is "A"
'''
    manifest = _manifest(source)
    row = manifest["pages"][0]["elements"][0]
    with pytest.raises(Namel3ssError):
        apply_edit_to_source(
          source,
          "insert",
          {"page": "home", "element_id": row["element_id"], "position": "inside_end"},
          {"type": "text", "value": "Bad"},
          SessionState(),
        )


def test_move_down_reorders():
    source = '''page "home":
  title is "First"
  text is "Second"
'''
    manifest = _manifest(source)
    first = manifest["pages"][0]["elements"][0]
    updated, _, manifest_out = apply_edit_to_source(
        source,
        "move_down",
        {"page": "home", "element_id": first["element_id"]},
        "",
        SessionState(),
    )
    assert "title is \"First\"" in updated
    elements = manifest_out["pages"][0]["elements"]
    assert elements[0]["type"] == "text"
    assert elements[1]["type"] == "title"
