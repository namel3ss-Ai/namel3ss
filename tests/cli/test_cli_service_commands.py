from __future__ import annotations

from pathlib import Path

from namel3ss.cli.main import main


SERVICE_APP = '''spec is "1.0"

capabilities:
  service

flow "demo":
  return "ok"
'''


NO_SERVICE_APP = '''spec is "1.0"

flow "demo":
  return "ok"
'''



def test_serve_dry_succeeds_with_service_capability(tmp_path: Path, capsys) -> None:
    app_path = tmp_path / "app.ai"
    app_path.write_text(SERVICE_APP, encoding="utf-8")

    code = main(["serve", app_path.as_posix(), "--dry", "--port", "8899"])
    captured = capsys.readouterr()

    assert code == 0
    assert "http://127.0.0.1:8899/" in captured.out



def test_serve_requires_service_capability(tmp_path: Path, capsys) -> None:
    app_path = tmp_path / "app.ai"
    app_path.write_text(NO_SERVICE_APP, encoding="utf-8")

    code = main(["serve", app_path.as_posix(), "--dry"])
    captured = capsys.readouterr()

    assert code == 1
    assert "service" in captured.err.lower()


def test_run_service_requires_service_capability(tmp_path: Path, capsys) -> None:
    app_path = tmp_path / "app.ai"
    app_path.write_text(NO_SERVICE_APP, encoding="utf-8")

    code = main(["run", app_path.as_posix(), "--service", "--dry"])
    captured = capsys.readouterr()

    assert code == 1
    assert "service" in captured.err.lower()


def test_run_service_dry_succeeds_with_service_capability(tmp_path: Path, capsys) -> None:
    app_path = tmp_path / "app.ai"
    app_path.write_text(SERVICE_APP, encoding="utf-8")

    code = main(["run", app_path.as_posix(), "--service", "--dry", "--port", "8898"])
    captured = capsys.readouterr()

    assert code == 0
    assert "Service runner dry http://127.0.0.1:8898/health" in captured.out



def test_studio_connect_dispatches_to_remote_command(monkeypatch) -> None:
    seen: dict[str, object] = {}

    def fake_connect(args: list[str]) -> int:
        seen["args"] = list(args)
        return 9

    monkeypatch.setattr("namel3ss.cli.main.run_studio_connect_command", fake_connect)

    code = main(["studio", "connect", "s000123", "--host", "127.0.0.1", "--port", "8787"])

    assert code == 9
    assert seen["args"] == ["s000123", "--host", "127.0.0.1", "--port", "8787"]



def test_session_command_dispatches(monkeypatch) -> None:
    seen: dict[str, object] = {}

    def fake_session(args: list[str]) -> int:
        seen["args"] = list(args)
        return 5

    monkeypatch.setattr("namel3ss.cli.main.run_session_command", fake_session)

    code = main(["session", "list", "--host", "localhost"])

    assert code == 5
    assert seen["args"] == ["list", "--host", "localhost"]
