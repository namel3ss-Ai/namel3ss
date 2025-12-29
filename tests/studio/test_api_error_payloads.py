import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.payload import build_error_from_exception
from namel3ss.runtime.store.memory_store import MemoryStore
from namel3ss.studio.api import execute_action
from namel3ss.studio.edit.ops import apply_edit_to_source
from namel3ss.ui.manifest import build_manifest
from tests.conftest import lower_ir_program


def test_insert_row_error_payload():
    source = 'spec is "1.0"\n\npage "home":\n  row:\n    column:\n      text is "hi"\n'
    program = lower_ir_program(source)
    manifest = build_manifest(program, state={}, store=MemoryStore())
    row_el = manifest["pages"][0]["elements"][0]
    with pytest.raises(Exception) as excinfo:
        apply_edit_to_source(
            source,
            "insert",
            {"page": "home", "element_id": row_el["element_id"], "position": "inside_end"},
            {"type": "text"},
        )
    assert isinstance(excinfo.value, Namel3ssError)
    payload = build_error_from_exception(excinfo.value, kind="edit", source=source)
    assert payload["ok"] is False
    assert payload["kind"] == "edit"
    assert payload.get("details", {}).get("expected") == "column"
    assert payload.get("details", {}).get("got") == "text"
    assert payload.get("location") is not None


def test_execute_action_unknown_returns_error_payload():
    source = 'spec is "1.0"\n\nflow "demo":\n  return "ok"\n'
    payload = execute_action(source, session=None, action_id="unknown", payload={})
    assert payload["ok"] is False
    assert payload.get("kind") == "engine"
    assert "Unknown action" in payload.get("error", "")
