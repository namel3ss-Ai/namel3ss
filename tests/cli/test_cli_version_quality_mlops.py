from __future__ import annotations

import json
from pathlib import Path

from namel3ss.cli.main import main as cli_main


def _write_app(tmp_path: Path) -> Path:
    app = tmp_path / "app.ai"
    app.write_text(
        'spec is "1.0"\n\ncapabilities:\n  versioning_quality_mlops\n\nflow "demo_flow":\n  return "ok"\n',
        encoding="utf-8",
    )
    return app


def test_cli_version_quality_and_mlops_commands(tmp_path: Path, capsys, monkeypatch) -> None:
    _write_app(tmp_path)
    registry_file = tmp_path / "registry_ops.json"
    (tmp_path / "mlops.yaml").write_text(
        f"registry_url: {registry_file.as_uri()}\nproject_name: demo\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    assert cli_main(["version", "add", "flow:demo_flow", "1.0", "--json"]) == 0
    version_add = json.loads(capsys.readouterr().out)
    assert version_add["ok"] is True
    assert version_add["action"] == "add"

    assert cli_main(["version", "list", "--json"]) == 0
    version_list = json.loads(capsys.readouterr().out)
    assert version_list["count"] == 1
    assert version_list["items"][0]["entity"] == "demo_flow"

    assert cli_main(["quality", "check", "--json"]) == 0
    quality = json.loads(capsys.readouterr().out)
    assert quality["ok"] is True

    assert (
        cli_main(
            [
                "mlops",
                "register-model",
                "base",
                "1.0",
                "--artifact-uri",
                "model://base/1.0",
                "--dataset",
                "faq-dataset@1.0.0",
                "--metric",
                "accuracy=0.9",
                "--json",
            ]
        )
        == 0
    )
    register = json.loads(capsys.readouterr().out)
    assert register["ok"] is True
    assert register["queued"] is False

    assert cli_main(["mlops", "get-model", "base", "1.0", "--json"]) == 0
    fetched = json.loads(capsys.readouterr().out)
    assert fetched["ok"] is True
    assert fetched["model"]["name"] == "base"

    assert cli_main(["mlops", "list-models", "--json"]) == 0
    listed_models = json.loads(capsys.readouterr().out)
    assert listed_models["ok"] is True
    assert listed_models["count"] >= 1
