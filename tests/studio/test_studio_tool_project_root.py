from __future__ import annotations

from pathlib import Path

from namel3ss.studio import api
from namel3ss.studio.session import SessionState


APP_SOURCE = '''
spec is "1.0"

tool "echo":
  implemented using python

  input:
    text is text

  output:
    text is text

flow "demo":
  let result is echo:
    text is "hi"
  return result

page "home":
  button "Run":
    calls flow "demo"
'''.lstrip()


def _write_tool_project(tmp_path: Path) -> Path:
    app_file = tmp_path / "app.ai"
    app_file.write_text(APP_SOURCE, encoding="utf-8")
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir(parents=True, exist_ok=True)
    (tools_dir / "echo.py").write_text(
        "def run(payload):\n    return {\"text\": payload.get(\"text\", \"\")}\n",
        encoding="utf-8",
    )
    bindings_dir = tmp_path / ".namel3ss"
    bindings_dir.mkdir(parents=True, exist_ok=True)
    (bindings_dir / "tools.yaml").write_text(
        'tools:\n  "echo":\n    kind: "python"\n    entry: "tools.echo:run"\n',
        encoding="utf-8",
    )
    return app_file


def test_tool_project_root_required(tmp_path: Path):
    app_file = _write_tool_project(tmp_path)
    session = SessionState()
    failure = api.execute_action(APP_SOURCE, session, "page.home.button.run", {}, app_path=None)
    assert failure["ok"] is False
    assert "Studio needs an app file path" in failure["error"]

    success = api.execute_action(APP_SOURCE, SessionState(), "page.home.button.run", {}, app_path=str(app_file))
    assert success["ok"] is True


def test_execute_action_uses_project_loader(monkeypatch, tmp_path: Path):
    app_file = _write_tool_project(tmp_path)
    called = {}
    real_load_project = api.load_project

    def _wrapped_load_project(path, *args, **kwargs):
        called["path"] = Path(path)
        return real_load_project(path, *args, **kwargs)

    monkeypatch.setattr(api, "load_project", _wrapped_load_project)
    result = api.execute_action(APP_SOURCE, SessionState(), "page.home.button.run", {}, app_path=str(app_file))
    assert result["ok"] is True
    assert called.get("path") == app_file
