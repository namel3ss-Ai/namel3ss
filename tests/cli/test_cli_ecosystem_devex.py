from __future__ import annotations

import json
from pathlib import Path

from namel3ss.cli.main import main as cli_main


CONTRACT_APP = '''spec is "1.0"

contract flow "hello":
  input:
    name is text
  output:
    result is text

flow "hello": purity is "pure"
  return "ok"
'''


def test_cli_ecosystem_commands(tmp_path: Path, capsys, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    assert cli_main(["init", "demo_app", "--json"]) == 0
    init_payload = json.loads(capsys.readouterr().out)
    assert init_payload["ok"] is True
    project_root = Path(init_payload["path"])
    assert (project_root / "app.ai").exists()
    assert (project_root / "models.yaml").exists()
    assert (project_root / "dataset_registry.yaml").exists()

    monkeypatch.chdir(project_root)

    assert cli_main(["tutorial", "list", "--json"]) == 0
    tutorials = json.loads(capsys.readouterr().out)
    assert tutorials["ok"] is True
    assert tutorials["count"] >= 1

    assert cli_main(["tutorial", "run", "basics", "--auto", "--json"]) == 0
    run_payload = json.loads(capsys.readouterr().out)
    assert run_payload["ok"] is True
    assert run_payload["completed"] is True

    (project_root / "app.ai").write_text(CONTRACT_APP, encoding="utf-8")

    assert cli_main(["scaffold", "test", "hello", "--json"]) == 0
    scaffold_payload = json.loads(capsys.readouterr().out)
    assert scaffold_payload["ok"] is True
    assert Path(scaffold_payload["path"]).exists()

    assert cli_main(["package", "build", "--out", "dist", "--json"]) == 0
    package_payload = json.loads(capsys.readouterr().out)
    assert package_payload["ok"] is True
    assert Path(package_payload["archive"]).exists()

    assert cli_main(["lsp", "check", "app.ai", "--json"]) == 0
    lsp_payload = json.loads(capsys.readouterr().out)
    assert lsp_payload["ok"] is True
    assert lsp_payload["count"] == 0

    assert cli_main(["docs", "--offline"]) == 0
    out = capsys.readouterr().out
    assert "Offline docs:" in out
