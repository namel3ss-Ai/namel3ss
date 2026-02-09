from __future__ import annotations

import json

from namel3ss.cli.main import main
from namel3ss.cli.targets import parse_target


APP_SOURCE = '''
spec is "1.0"

flow "demo":
  return "ok"
'''.lstrip()


def _write_app(tmp_path):
    path = tmp_path / "app.ai"
    path.write_text(APP_SOURCE, encoding="utf-8")
    return path


def test_embedded_target_is_resolved() -> None:
    target = parse_target("embedded")
    assert target.name == "embedded"
    assert target.process_model == "embedded"


def test_run_embedded_target_executes_without_server(tmp_path, capsys, monkeypatch) -> None:
    app_path = _write_app(tmp_path)
    monkeypatch.chdir(tmp_path)
    code = main(["run", app_path.as_posix(), "--target", "embedded", "--json"])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert "result" in payload
