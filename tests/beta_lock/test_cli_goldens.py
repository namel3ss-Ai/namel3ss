from __future__ import annotations

import json
from pathlib import Path

from namel3ss.cli.main import main as cli_main

FIXTURE_DIR = Path("tests/fixtures")

UI_SOURCE = '''spec is "1.0"

record "User":
  name string

flow "demo":
  return "ok"

page "home":
  button "Run":
    calls flow "demo"
  form is "User"
'''


def _load_json_fixture(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def _load_text_fixture(name: str) -> str:
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


def test_cli_ui_manifest_golden(tmp_path, capsys):
    app_path = tmp_path / "app.ai"
    app_path.write_text(UI_SOURCE, encoding="utf-8")
    code = cli_main([str(app_path), "ui"])
    out = capsys.readouterr().out
    assert code == 0
    payload = json.loads(out)
    expected = _load_json_fixture("ui_manifest_golden.json")
    assert payload == expected


def test_cli_actions_golden(tmp_path, capsys):
    app_path = tmp_path / "app.ai"
    app_path.write_text(UI_SOURCE, encoding="utf-8")
    code = cli_main([str(app_path), "actions"])
    out = capsys.readouterr().out
    assert code == 0
    expected = _load_text_fixture("actions_plain_golden.txt")
    assert out == expected

    code = cli_main([str(app_path), "actions", "json"])
    out = capsys.readouterr().out
    payload = json.loads(out)
    expected_json = _load_json_fixture("actions_json_golden.json")
    assert code == 0
    assert payload == expected_json


def test_cli_eval_report_golden(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parents[2]
    json_path = tmp_path / "eval_report.json"
    txt_path = tmp_path / "eval_report.txt"
    monkeypatch.chdir(root)
    code = cli_main(["eval", "--json", str(json_path), "--txt", str(txt_path)])
    assert code == 0
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    expected = _load_json_fixture("eval_report_golden.json")
    assert "namel3ss_version" in payload
    expected["namel3ss_version"] = payload["namel3ss_version"]
    assert payload == expected
    assert txt_path.read_text(encoding="utf-8") == _load_text_fixture("eval_report_golden.txt")
