from __future__ import annotations

from pathlib import Path

from namel3ss import contract as build_contract
from namel3ss.contract.builder import build_contract_pack
from namel3ss.contract.render_plain import render_exists


SOURCE = '''spec is "1.0"

record "Item":
  name text

flow "demo":
  return "ok"

page "home":
  button "Run":
    calls flow "demo"
'''


def _write_and_build(tmp_path: Path) -> tuple[str, str]:
    app_path = tmp_path / "app.ai"
    app_path.write_text(SOURCE, encoding="utf-8")
    contract_obj = build_contract(SOURCE)
    setattr(contract_obj.program, "app_path", app_path)
    setattr(contract_obj.program, "project_root", tmp_path)
    build_contract_pack(contract_obj)
    last_json = tmp_path / ".namel3ss" / "contract" / "last.json"
    last_plain = tmp_path / ".namel3ss" / "contract" / "last.plain"
    return last_json.read_text(encoding="utf-8"), last_plain.read_text(encoding="utf-8")


def test_contract_pack_is_deterministic(tmp_path: Path) -> None:
    json_first, plain_first = _write_and_build(tmp_path)
    json_second, plain_second = _write_and_build(tmp_path)
    assert json_first == json_second
    assert plain_first == plain_second


def test_render_exists_reports_no_warnings(tmp_path: Path) -> None:
    contract_obj = build_contract(SOURCE)
    setattr(contract_obj.program, "project_root", tmp_path)
    pack = build_contract_pack(contract_obj)
    text = render_exists(pack)
    assert "Warnings" in text
    assert "none recorded" in text
