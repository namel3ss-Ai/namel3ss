from __future__ import annotations

from pathlib import Path

from namel3ss.cli.main import main as cli_main


def _write_app_without_capability(tmp_path: Path) -> None:
    (tmp_path / "app.ai").write_text(
        'spec is "1.0"\n\nflow "demo_flow":\n  return "ok"\n',
        encoding="utf-8",
    )


def test_version_quality_mlops_commands_require_capability(tmp_path: Path, capsys, monkeypatch) -> None:
    _write_app_without_capability(tmp_path)
    monkeypatch.chdir(tmp_path)

    commands = [
        ["version", "list", "--json"],
        ["quality", "check", "--json"],
        ["mlops", "list-models", "--json"],
    ]
    for command in commands:
        assert cli_main(command) == 1
        captured = capsys.readouterr()
        assert "versioning_quality_mlops" in captured.err
