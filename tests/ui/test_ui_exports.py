import json
from pathlib import Path

from namel3ss.runtime.store.memory_store import MemoryStore
from namel3ss.ui.export.actions import build_actions_export
from namel3ss.ui.export.schema import build_schema_export
from namel3ss.ui.export.ui import build_ui_export
from namel3ss.ui.export.writer import write_ui_exports
from namel3ss.ui.manifest import build_manifest
from tests.conftest import lower_ir_program


SOURCE = '''spec is "1.0"

record "User":
  name text must be present
  email text must match pattern ".*@.*"

record "Audit":
  note text

flow "demo":
  return "ok"

page "Home":
  form is "User"
  table is "User"
  button "Run":
    calls flow "demo"
'''


def test_ui_exports_structure_and_order(tmp_path: Path) -> None:
    program = lower_ir_program(SOURCE)
    manifest = build_manifest(program, state={}, store=MemoryStore())
    ui_export = build_ui_export(manifest)
    actions_export = build_actions_export(manifest)
    schema_export = build_schema_export(program, manifest)

    assert ui_export["schema_version"] == "1"
    assert actions_export["schema_version"] == "1"
    assert schema_export["schema_version"] == "1"

    table = next(
        el
        for page in ui_export["pages"]
        for el in page.get("elements", [])
        if el.get("type") == "table"
    )
    assert "rows" not in table

    action_ids = [item["id"] for item in actions_export["actions"]]
    assert action_ids == sorted(action_ids)
    assert "page.home.button.run" in action_ids
    assert "page.home.form.user" in action_ids

    records = schema_export["records"]
    assert [record["name"] for record in records] == ["User"]
    fields = records[0]["fields"]
    assert [field["name"] for field in fields] == ["name", "email"]
    assert fields[0]["constraints"][0]["kind"] == "present"
    assert fields[1]["constraints"][0]["kind"] == "pattern"


def test_ui_export_writer_is_deterministic(tmp_path: Path) -> None:
    program = lower_ir_program(SOURCE)
    manifest = build_manifest(program, state={}, store=MemoryStore())
    ui_export = build_ui_export(manifest)
    actions_export = build_actions_export(manifest)
    schema_export = build_schema_export(program, manifest)

    first = write_ui_exports(tmp_path, ui=ui_export, actions=actions_export, schema=schema_export)
    ui_path = Path(first["ui_path"])
    text_first = ui_path.read_text(encoding="utf-8")

    second = write_ui_exports(tmp_path, ui=ui_export, actions=actions_export, schema=schema_export)
    assert first == second
    text_second = ui_path.read_text(encoding="utf-8")
    assert text_first == text_second

    payload = json.loads(text_first)
    assert payload["schema_version"] == "1"
