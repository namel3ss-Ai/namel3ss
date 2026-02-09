from __future__ import annotations

import json
from pathlib import Path

from namel3ss.cli.main import main


APP_SOURCE = '''spec is "1.0"

capabilities:
  app_packaging
  app_permissions

permissions:
  ai:
    call: denied
    tools: denied
  uploads:
    read: denied
    write: denied
  ui_state:
    persistent_write: denied
  navigation:
    change_page: denied

flow "demo":
  return "ok"

page "Home":
  text is "Ready"
'''


def _build_archive(tmp_path: Path, capsys) -> Path:
    app_path = tmp_path / "app.ai"
    app_path.write_text(APP_SOURCE, encoding="utf-8")
    assert main(["build", app_path.as_posix()]) == 0
    out = capsys.readouterr().out.strip()
    return Path(out)


def test_inspect_outputs_stable_machine_json(tmp_path: Path, capsys) -> None:
    archive = _build_archive(tmp_path, capsys)

    code_one = main(["inspect", archive.as_posix()])
    out_one = capsys.readouterr().out
    code_two = main(["inspect", archive.as_posix()])
    out_two = capsys.readouterr().out

    assert code_one == 0
    assert code_two == 0
    assert out_one == out_two

    payload = json.loads(out_one)
    assert payload["app"] == "app"
    assert payload["checksum"]
    assert isinstance(payload["permissions"], dict)
    assert isinstance(payload["pages"], list)
    assert isinstance(payload["ui_state"], dict)
    assert isinstance(payload["capabilities"], list)
    assert payload["namel3ss_version"]


def test_inspect_accepts_source_path(tmp_path: Path, capsys) -> None:
    app_path = tmp_path / "app.ai"
    app_path.write_text(APP_SOURCE, encoding="utf-8")

    code = main(["inspect", app_path.as_posix()])
    out = capsys.readouterr().out

    assert code == 0
    payload = json.loads(out)
    assert payload["app"] == "app"
