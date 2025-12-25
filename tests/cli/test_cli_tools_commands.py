from __future__ import annotations

import json
from pathlib import Path

from namel3ss.cli.main import main as cli_main


TOOL_SOURCE = '''tool "get data":
  implemented using python

  input:
    url is text

  output:
    data is json

flow "demo":
  return "ok"
'''


def test_tools_status_reports_missing_bindings(tmp_path: Path, monkeypatch, capsys) -> None:
    (tmp_path / "app.ai").write_text(TOOL_SOURCE, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert cli_main(["tools", "status", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["bindings_present"] is False
    assert "get data" in data["missing_bindings"]
    assert data["unused_bindings"] == []
    assert data["summary"]["missing"] == 1


def test_tools_status_reports_unused_bindings(tmp_path: Path, monkeypatch, capsys) -> None:
    (tmp_path / "app.ai").write_text(TOOL_SOURCE, encoding="utf-8")
    tools_dir = tmp_path / ".namel3ss"
    tools_dir.mkdir()
    (tools_dir / "tools.yaml").write_text(
        'tools:\n  "unused tool":\n    kind: "python"\n    entry: "tools.unused:run"\n',
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    assert cli_main(["tools", "status", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert "unused tool" in data["unused_bindings"]
    assert data["summary"]["unused"] == 1


def test_tools_bind_writes_binding(tmp_path: Path, monkeypatch, capsys) -> None:
    (tmp_path / "app.ai").write_text(TOOL_SOURCE, encoding="utf-8")
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()
    (tools_dir / "http.py").write_text("def run(payload: dict) -> dict:\n    return {}\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert cli_main(["tools", "bind", "get data", "--entry", "tools.http:run", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["entry"] == "tools.http:run"
    bindings_path = tmp_path / ".namel3ss" / "tools.yaml"
    contents = bindings_path.read_text(encoding="utf-8")
    assert '"get data"' in contents
    assert 'kind: "python"' in contents
    assert 'entry: "tools.http:run"' in contents


def test_tools_bind_rejects_invalid_entry(tmp_path: Path, monkeypatch, capsys) -> None:
    (tmp_path / "app.ai").write_text(TOOL_SOURCE, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    rc = cli_main(["tools", "bind", "get data", "--entry", "badentry"])
    assert rc == 1
    captured = capsys.readouterr()
    text = captured.out + captured.err
    assert "module:function" in text


def test_tools_bind_from_app_dry(tmp_path: Path, monkeypatch, capsys) -> None:
    (tmp_path / "app.ai").write_text(TOOL_SOURCE, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert cli_main(["tools", "bind", "--from-app", "--dry", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["status"] == "dry_run"
    assert "get data" in data["missing_bindings"]
    assert (tmp_path / ".namel3ss" / "tools.yaml").exists() is False


def test_tools_bind_auto_alias(tmp_path: Path, monkeypatch, capsys) -> None:
    (tmp_path / "app.ai").write_text(TOOL_SOURCE, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert cli_main(["tools", "bind", "--auto", "--dry", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["status"] == "dry_run"


def test_tools_bind_from_app_writes_bindings_and_stubs(tmp_path: Path, monkeypatch, capsys) -> None:
    (tmp_path / "app.ai").write_text(TOOL_SOURCE, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert cli_main(["tools", "bind", "--from-app", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    bindings_path = tmp_path / ".namel3ss" / "tools.yaml"
    assert bindings_path.exists()
    assert "get data" in data["missing_bound"]
    stub_path = tmp_path / "tools" / "get_data.py"
    assert stub_path.exists()
    assert "def run" in stub_path.read_text(encoding="utf-8")


def test_tools_bind_from_app_conflict_requires_overwrite(tmp_path: Path, monkeypatch, capsys) -> None:
    (tmp_path / "app.ai").write_text(TOOL_SOURCE, encoding="utf-8")
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()
    (tools_dir / "get_data.py").write_text("# existing", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    rc = cli_main(["tools", "bind", "--from-app"])
    assert rc == 1
    captured = capsys.readouterr()
    text = captured.out + captured.err
    assert "--overwrite" in text


def test_tools_list_shows_pack_and_declared(tmp_path: Path, monkeypatch, capsys) -> None:
    source = '''tool "slugify text":
  implemented using python

  input:
    text is text

  output:
    text is text

tool "get data":
  implemented using python

  input:
    url is text

  output:
    data is json

flow "demo":
  return "ok"
'''
    (tmp_path / "app.ai").write_text(source, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert cli_main(["tools", "list", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    pack_names = [item["name"] for item in data["packs"]]
    declared_names = [item["name"] for item in data["declared"]]
    assert "slugify text" in pack_names
    assert "get data" in declared_names


def test_tools_list_includes_runner(tmp_path: Path, monkeypatch, capsys) -> None:
    (tmp_path / "app.ai").write_text(TOOL_SOURCE, encoding="utf-8")
    tools_dir = tmp_path / ".namel3ss"
    tools_dir.mkdir()
    (tools_dir / "tools.yaml").write_text(
        'tools:\n'
        '  "get data":\n'
        '    kind: "python"\n'
        '    entry: "tools.http:run"\n'
        '    runner: "service"\n'
        '    url: "http://127.0.0.1:8787/tools"\n',
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    assert cli_main(["tools", "list", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    binding = next(item for item in data["bindings"] if item["name"] == "get data")
    assert binding["runner"] == "service"


def test_tools_search_finds_pack_tool(tmp_path: Path, monkeypatch, capsys) -> None:
    (tmp_path / "app.ai").write_text(TOOL_SOURCE, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert cli_main(["tools", "search", "date", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    names = [item["name"] for item in data["results"]]
    assert "get current date and time" in names


def test_tools_set_runner_updates_binding(tmp_path: Path, monkeypatch, capsys) -> None:
    (tmp_path / "app.ai").write_text(TOOL_SOURCE, encoding="utf-8")
    tools_dir = tmp_path / ".namel3ss"
    tools_dir.mkdir()
    (tools_dir / "tools.yaml").write_text(
        'tools:\n  "get data":\n    kind: "python"\n    entry: "tools.http:run"\n',
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    assert (
        cli_main(
            [
                "tools",
                "set-runner",
                "get data",
                "--runner",
                "service",
                "--url",
                "http://127.0.0.1:8787/tools",
                "--json",
            ]
        )
        == 0
    )
    data = json.loads(capsys.readouterr().out)
    assert data["runner"] == "service"
    contents = (tools_dir / "tools.yaml").read_text(encoding="utf-8")
    assert 'runner: "service"' in contents
    assert 'url: "http://127.0.0.1:8787/tools"' in contents


def test_tools_unbind_removes_binding(tmp_path: Path, monkeypatch, capsys) -> None:
    (tmp_path / "app.ai").write_text(TOOL_SOURCE, encoding="utf-8")
    tools_dir = tmp_path / ".namel3ss"
    tools_dir.mkdir()
    (tools_dir / "tools.yaml").write_text(
        'tools:\n  "get data":\n    kind: "python"\n    entry: "tools.http:run"\n',
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    assert cli_main(["tools", "unbind", "get data", "--json"]) == 0
    contents = (tools_dir / "tools.yaml").read_text(encoding="utf-8")
    assert "get data" not in contents


def test_tools_format_normalizes_order(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "app.ai").write_text(TOOL_SOURCE, encoding="utf-8")
    tools_dir = tmp_path / ".namel3ss"
    tools_dir.mkdir()
    (tools_dir / "tools.yaml").write_text(
        'tools:\n  "b":\n    kind: "python"\n    entry: "tools.b:run"\n  "a":\n    kind: "python"\n    entry: "tools.a:run"\n',
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    assert cli_main(["tools", "format"]) == 0
    contents = (tools_dir / "tools.yaml").read_text(encoding="utf-8")
    assert contents.index('"a"') < contents.index('"b"')
