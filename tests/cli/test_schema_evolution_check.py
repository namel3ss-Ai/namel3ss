from __future__ import annotations

from namel3ss.cli.check_mode import run_check
from namel3ss.determinism import canonical_json_dumps
from namel3ss.schema.evolution import build_schema_snapshot, workspace_snapshot_path
from tests.conftest import lower_ir_program


BASE_SOURCE = '''spec is "1.0"

record "Note":
  title text

flow "demo":
  return "ok"
'''

CHANGED_SOURCE = '''spec is "1.0"

record "Note":
  title number

flow "demo":
  return "ok"
'''


def test_check_warns_on_breaking_schema(tmp_path, capsys) -> None:
    app_path = tmp_path / "app.ai"
    app_path.write_text(CHANGED_SOURCE, encoding="utf-8")
    base_program = lower_ir_program(BASE_SOURCE)
    snapshot = build_schema_snapshot(base_program.records)
    snapshot_path = workspace_snapshot_path(tmp_path)
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_text(canonical_json_dumps(snapshot, pretty=True), encoding="utf-8")

    rc = run_check(app_path.as_posix())
    out = capsys.readouterr().out.lower()
    assert rc == 0
    assert "schema change is incompatible" in out
