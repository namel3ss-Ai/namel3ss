from __future__ import annotations

import json
from pathlib import Path

import pytest

from namel3ss.cli.main import main as cli_main
from namel3ss.runtime.tools.python_env import venv_python_path


TOOL_SOURCE = '''tool "greeter":
  implemented using python

  input:
    name is text

  output:
    message is text

flow "demo":
  return "ok"
'''


def test_doctor_warns_when_deps_missing(tmp_path: Path, monkeypatch, capsys) -> None:
    (tmp_path / "app.ai").write_text(TOOL_SOURCE, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert cli_main(["doctor", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    checks = {c["id"]: c for c in data["checks"]}
    assert checks["python_deps"]["status"] == "warning"


def test_doctor_warns_when_venv_missing(tmp_path: Path, monkeypatch, capsys) -> None:
    (tmp_path / "app.ai").write_text(TOOL_SOURCE, encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("requests==2.31.0\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert cli_main(["doctor", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    checks = {c["id"]: c for c in data["checks"]}
    assert checks["python_venv"]["status"] == "warning"


def test_doctor_ok_when_venv_present(tmp_path: Path, monkeypatch, capsys) -> None:
    (tmp_path / "app.ai").write_text(TOOL_SOURCE, encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("requests==2.31.0\n", encoding="utf-8")
    venv_path = tmp_path / ".venv"
    py_path = venv_python_path(venv_path)
    py_path.parent.mkdir(parents=True, exist_ok=True)
    py_path.write_text("", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert cli_main(["doctor", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    checks = {c["id"]: c for c in data["checks"]}
    assert checks["python_venv"]["status"] == "ok"


def test_doctor_invalid_entry_reports_error(tmp_path: Path, monkeypatch, capsys) -> None:
    (tmp_path / "app.ai").write_text(TOOL_SOURCE, encoding="utf-8")
    tools_dir = tmp_path / ".namel3ss"
    tools_dir.mkdir()
    (tools_dir / "tools.yaml").write_text(
        'tools:\n  "greeter":\n    kind: "python"\n    entry: "badentry"\n',
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    assert cli_main(["doctor", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    checks = {c["id"]: c for c in data["checks"]}
    assert checks["python_tool_entries"]["status"] == "error"


def test_doctor_warns_on_missing_binding_with_fix(tmp_path: Path, monkeypatch, capsys) -> None:
    (tmp_path / "app.ai").write_text(TOOL_SOURCE, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert cli_main(["doctor", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    checks = {c["id"]: c for c in data["checks"]}
    assert checks["python_tool_entries"]["status"] == "warning"
    assert "n3 tools bind" in checks["python_tool_entries"]["message"] or "n3 tools bind" in checks["python_tool_entries"]["fix"]


def test_doctor_warns_on_unused_binding(tmp_path: Path, monkeypatch, capsys) -> None:
    (tmp_path / "app.ai").write_text(TOOL_SOURCE, encoding="utf-8")
    tools_dir = tmp_path / ".namel3ss"
    tools_dir.mkdir()
    (tools_dir / "tools.yaml").write_text(
        'tools:\n  "unused tool":\n    kind: "python"\n    entry: "tools.unused:run"\n',
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    assert cli_main(["doctor", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    checks = {c["id"]: c for c in data["checks"]}
    assert checks["python_tool_unused_bindings"]["status"] == "warning"
