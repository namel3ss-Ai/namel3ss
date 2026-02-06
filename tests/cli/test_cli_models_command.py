from __future__ import annotations

import json
from pathlib import Path

from namel3ss.cli.main import main as cli_main


def _write_app(tmp_path: Path) -> Path:
    app = tmp_path / "app.ai"
    app.write_text('spec is "1.0"\n\nflow "demo_flow":\n  return "ok"\n', encoding="utf-8")
    return app


def test_cli_models_add_list_and_deprecate(tmp_path: Path, capsys, monkeypatch) -> None:
    _write_app(tmp_path)
    monkeypatch.chdir(tmp_path)

    assert (
        cli_main(
            [
                "models",
                "add",
                "gpt-4",
                "1.0",
                "--provider",
                "openai",
                "--domain",
                "general",
                "--tokens-per-second",
                "10",
                "--cost-per-token",
                "0.00001",
                "--privacy-level",
                "standard",
                "--json",
            ]
        )
        == 0
    )
    added = json.loads(capsys.readouterr().out)
    assert added["ok"] is True
    assert added["model"]["name"] == "gpt-4"
    assert added["model"]["status"] == "active"

    assert cli_main(["models", "list", "--json"]) == 0
    listed = json.loads(capsys.readouterr().out)
    assert listed["ok"] is True
    assert listed["count"] == 1
    assert listed["models"][0]["name"] == "gpt-4"

    assert cli_main(["models", "deprecate", "gpt-4", "1.0", "--json"]) == 0
    deprecated = json.loads(capsys.readouterr().out)
    assert deprecated["ok"] is True
    assert deprecated["model"]["status"] == "deprecated"
