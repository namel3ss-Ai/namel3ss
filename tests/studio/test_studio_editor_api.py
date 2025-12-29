from __future__ import annotations

from pathlib import Path

from namel3ss.studio import editor_api


def _find_position(source: str, needle: str) -> tuple[int, int]:
    for idx, line in enumerate(source.splitlines(), start=1):
        col = line.find(needle)
        if col != -1:
            return idx, col + 1
    raise AssertionError(f"{needle} not found")


def test_editor_fix_and_apply(tmp_path: Path) -> None:
    app_path = tmp_path / "app.ai"
    source = """
spec is "1.0"

record "Customer":
  name text

flow "create_customer":
  create "Customer" with state.customer as customer
  return "ok"
""".lstrip()
    app_path.write_text(source, encoding="utf-8")

    diagnostics = editor_api.diagnose_payload(str(app_path))
    diag = next(d for d in diagnostics["diagnostics"] if d["id"].startswith("governance.requires_flow_missing"))
    assert diag["fix_available"] is True

    fix = editor_api.fix_payload(str(app_path), {"file": diag["file"], "diagnostic_id": diag["id"]})
    assert fix["status"] == "ok"
    apply_resp = editor_api.apply_payload(str(app_path), {"edits": fix["edits"]})
    assert apply_resp["status"] == "ok"

    updated = app_path.read_text(encoding="utf-8")
    assert "requires identity.role" in updated
    assert not any(
        d["id"].startswith("governance.requires_flow_missing") for d in apply_resp["diagnostics"]
    )


def test_editor_rename_preview_and_apply(tmp_path: Path) -> None:
    app_path = tmp_path / "app.ai"
    source = """
spec is "1.0"

record "Customer":
  name text

flow "create_customer":
  create "Customer" with state.customer as customer
  return "ok"
""".lstrip()
    app_path.write_text(source, encoding="utf-8")

    line, column = _find_position(source, "Customer")
    rename = editor_api.rename_payload(
        str(app_path),
        {
            "file": "app.ai",
            "position": {"line": line, "column": column},
            "new_name": "Client",
        },
    )
    assert rename["status"] == "ok"
    apply_resp = editor_api.apply_payload(str(app_path), {"edits": rename["edits"]})
    assert apply_resp["status"] == "ok"
    updated = app_path.read_text(encoding="utf-8")
    assert "Client" in updated
    assert "Customer" not in updated
