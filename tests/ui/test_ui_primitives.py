from __future__ import annotations

from pathlib import Path

import pytest

from namel3ss.cli.app_loader import load_program
from namel3ss.config.loader import load_config
from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.store.memory_store import MemoryStore
from namel3ss.studio.api import get_ui_payload
from namel3ss.studio.session import SessionState
from namel3ss.ui.manifest import build_manifest
from namel3ss.validation_entrypoint import build_static_manifest
from tests.conftest import lower_ir_program


def test_number_and_view_manifest_defaults():
    source = '''
spec is "1.0"

record "User":
  name string

page "home":
  purpose is "Status"
  number:
    "active users"
    count of "User" as "Total users"
  view of "User"
'''.lstrip()
    manifest = build_manifest(lower_ir_program(source), state={}, store=None)
    page = manifest["pages"][0]
    assert page.get("purpose") == "Status"
    number = page["elements"][0]
    assert number["type"] == "number"
    assert [entry["kind"] for entry in number["entries"]] == ["phrase", "count"]
    assert number["entries"][0]["value"] == "active users"
    assert number["entries"][1]["record"] == "User"
    view = page["elements"][1]
    assert view["type"] == "view"
    assert view["representation"] == "list"
    assert view["record"] == "User"
    assert "id_field" in view


def test_view_rows_order_by_id():
    source = '''
spec is "1.0"

record "User":
  id number
  name text

page "home":
  view of "User"
'''.lstrip()
    program = lower_ir_program(source)
    store = MemoryStore()
    record = next(item for item in program.records if item.name == "User")
    store.save(record, {"id": 10, "name": "Ten"})
    store.save(record, {"id": 2, "name": "Two"})
    store.save(record, {"id": 7, "name": "Seven"})
    manifest = build_manifest(program, state={}, store=store)
    view = next(el for el in manifest["pages"][0]["elements"] if el["type"] == "view")
    assert [row["id"] for row in view["rows"]] == [2, 7, 10]


def test_compose_groups_children_stably():
    source = '''
spec is "1.0"

record "Metric":
  name string

page "home":
  compose stats:
    number:
      "revenue today"
    view of "Metric"
'''.lstrip()
    manifest = build_manifest(lower_ir_program(source), state={}, store=None)
    compose = manifest["pages"][0]["elements"][0]
    assert compose["type"] == "compose"
    assert compose["name"] == "stats"
    children = compose["children"]
    assert [child["type"] for child in children] == ["number", "view"]
    assert children[0]["entries"][0]["value"] == "revenue today"


def test_view_unknown_record_suggests_fix():
    source = '''
spec is "1.0"

record "User":
  name string

page "home":
  view of "Usesr"
'''.lstrip()
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "Did you mean" in str(exc.value)


def test_purpose_must_be_at_page_root():
    source = '''
spec is "1.0"

page "home":
  section:
    purpose is "Nope"
'''.lstrip()
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "Purpose must be declared at the page root" in str(exc.value)


def test_duplicate_pages_are_rejected():
    source = '''
spec is "1.0"

page "home":
  title is "One"

page "home":
  title is "Two"
'''.lstrip()
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "declared more than once" in str(exc.value)


def test_manifest_is_deterministic_for_view_and_number():
    source = '''
spec is "1.0"

record "User":
  name string

page "home":
  number:
    "active users"
  view of "User"
'''.lstrip()
    program = lower_ir_program(source)
    first = build_manifest(program, state={}, store=None)
    second = build_manifest(program, state={}, store=None)
    assert first == second


def test_static_manifest_matches_studio_for_view_number(tmp_path: Path):
    source = '''
spec is "1.0"

record "User":
  name string

page "home":
  purpose is "Overview"
  number:
    "active users"
  view of "User"
'''.lstrip()
    app_file = tmp_path / "app.ai"
    app_file.write_text(source, encoding="utf-8")
    program, _ = load_program(app_file.as_posix())
    config = load_config(app_path=app_file)
    warnings: list = []
    helper_manifest = build_static_manifest(program, config=config, state={}, store=None, warnings=warnings)
    studio_manifest = get_ui_payload(source, SessionState(), app_path=app_file.as_posix())
    assert helper_manifest.get("pages") == studio_manifest.get("pages")
    assert helper_manifest.get("ui") == studio_manifest.get("ui")


def test_button_calls_flow():
    source = '''
spec is "1.0"

flow "create_ticket":
  return "ok"

page "home":
  button "New Ticket":
    calls flow "create_ticket"
'''.lstrip()
    manifest = build_manifest(lower_ir_program(source), state={}, store=None)
    button = manifest["pages"][0]["elements"][0]
    assert button["action"]["flow"] == "create_ticket"
    assert manifest["actions"]["page.home.button.new_ticket"]["flow"] == "create_ticket"


def test_button_calls_missing_flow_errors():
    source = '''
spec is "1.0"

page "home":
  button "New Ticket":
    calls flow "create_ticket"
    '''.lstrip()
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "unknown flow" in str(exc.value).lower() or "missing flow" in str(exc.value).lower()
