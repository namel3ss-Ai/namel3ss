from __future__ import annotations

import json
import shutil
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

PACK_SOURCE = '''tool "slugify text":
  implemented using python

  input:
    text is text

  output:
    text is text

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
    assert checks["python_tool_invalid_bindings"]["status"] == "error"


def test_doctor_reports_missing_service_url(tmp_path: Path, monkeypatch, capsys) -> None:
    (tmp_path / "app.ai").write_text(TOOL_SOURCE, encoding="utf-8")
    tools_dir = tmp_path / ".namel3ss"
    tools_dir.mkdir()
    (tools_dir / "tools.yaml").write_text(
        'tools:\n  "greeter":\n    kind: "python"\n    entry: "tools.greeter:run"\n    runner: "service"\n',
        encoding="utf-8",
    )
    monkeypatch.delenv("N3_TOOL_SERVICE_URL", raising=False)
    monkeypatch.chdir(tmp_path)
    assert cli_main(["doctor", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    checks = {c["id"]: c for c in data["checks"]}
    assert checks["python_tool_service_urls"]["status"] == "error"


def test_doctor_reports_container_runtime_missing(tmp_path: Path, monkeypatch, capsys) -> None:
    (tmp_path / "app.ai").write_text(TOOL_SOURCE, encoding="utf-8")
    tools_dir = tmp_path / ".namel3ss"
    tools_dir.mkdir()
    (tools_dir / "tools.yaml").write_text(
        'tools:\n'
        '  "greeter":\n'
        '    kind: "python"\n'
        '    entry: "tools.greeter:run"\n'
        '    runner: "container"\n'
        '    image: "ghcr.io/namel3ss/tools:latest"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr("namel3ss.tools.health.analyze.detect_container_runtime", lambda: None)
    monkeypatch.chdir(tmp_path)
    assert cli_main(["doctor", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    checks = {c["id"]: c for c in data["checks"]}
    assert checks["python_tool_container_runtime"]["status"] == "error"


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


def test_doctor_skips_bindings_for_builtin_pack(tmp_path: Path, monkeypatch, capsys) -> None:
    (tmp_path / "app.ai").write_text(PACK_SOURCE, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert cli_main(["doctor", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    checks = {c["id"]: c for c in data["checks"]}
    assert checks["python_tool_entries"]["status"] != "warning"


def test_doctor_reports_tool_collisions(tmp_path: Path, monkeypatch, capsys) -> None:
    (tmp_path / "app.ai").write_text(PACK_SOURCE, encoding="utf-8")
    tools_dir = tmp_path / ".namel3ss"
    tools_dir.mkdir()
    (tools_dir / "tools.yaml").write_text(
        'tools:\n  "slugify text":\n    kind: "python"\n    entry: "tools.custom:run"\n',
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    assert cli_main(["doctor", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    checks = {c["id"]: c for c in data["checks"]}
    assert checks["python_tool_collisions"]["status"] == "error"


def test_doctor_warns_on_unverified_pack(tmp_path: Path, monkeypatch, capsys) -> None:
    (tmp_path / "app.ai").write_text('flow "demo":\n  return "ok"\n', encoding="utf-8")
    fixture_root = Path(__file__).resolve().parents[1] / "fixtures" / "packs" / "pack_good_unverified"
    pack_dest = tmp_path / ".namel3ss" / "packs" / "sample.unverified"
    shutil.copytree(fixture_root, pack_dest)
    monkeypatch.chdir(tmp_path)
    assert cli_main(["doctor", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    messages = [check["message"] for check in data["checks"]]
    assert any("unverified" in message.lower() for message in messages)
