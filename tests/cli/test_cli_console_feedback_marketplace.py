from __future__ import annotations

import json
from pathlib import Path

from namel3ss.cli.main import main as cli_main
from namel3ss.feedback import append_feedback_entry



def _write_app(tmp_path: Path) -> Path:
    app = tmp_path / "app.ai"
    app.write_text('spec is "1.0"\n\nflow "demo":\n  return "ok"\n', encoding="utf-8")
    return app



def _write_models(tmp_path: Path) -> None:
    models = tmp_path / ".namel3ss" / "models.yaml"
    models.parent.mkdir(parents=True, exist_ok=True)
    models.write_text(
        "models:\n"
        "  base:\n"
        "    version: 1.0\n"
        "    image: repo/base:1\n"
        "  candidate:\n"
        "    version: 1.1\n"
        "    image: repo/candidate:1\n",
        encoding="utf-8",
    )



def _write_market_item(tmp_path: Path) -> Path:
    item_root = tmp_path / "item"
    item_root.mkdir(parents=True, exist_ok=True)
    (item_root / "market_flow.ai").write_text('flow "market_demo":\n  return "ok"\n', encoding="utf-8")
    (item_root / "manifest.yaml").write_text(
        "name: demo.flow\n"
        "version: 0.1.0\n"
        "type: flow\n"
        "description: Demo marketplace flow\n"
        "author: test\n"
        "license: MIT\n"
        "files:\n"
        "  - market_flow.ai\n",
        encoding="utf-8",
    )
    return item_root



def test_cli_console_dry_run(tmp_path: Path, capsys, monkeypatch) -> None:
    _write_app(tmp_path)
    monkeypatch.chdir(tmp_path)
    assert cli_main(["console", "--dry"]) == 0



def test_cli_feedback_and_retrain(tmp_path: Path, capsys, monkeypatch) -> None:
    app = _write_app(tmp_path)
    monkeypatch.chdir(tmp_path)
    append_feedback_entry(app.parent, app, flow_name="demo", input_id="i1", rating="bad")

    assert cli_main(["feedback", "list", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["count"] == 1

    assert cli_main(["retrain", "schedule", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert "output_path" in payload



def test_cli_model_canary_and_marketplace(tmp_path: Path, capsys, monkeypatch) -> None:
    _write_app(tmp_path)
    _write_models(tmp_path)
    item_root = _write_market_item(tmp_path)
    monkeypatch.chdir(tmp_path)

    assert cli_main(["model", "canary", "base", "candidate", "0.5", "--json"]) == 0
    model_payload = json.loads(capsys.readouterr().out)
    assert model_payload["primary_model"] == "base"

    assert cli_main(["marketplace", "publish", str(item_root), "--json"]) == 0
    publish_payload = json.loads(capsys.readouterr().out)
    assert publish_payload["ok"] is True

    assert cli_main(["marketplace", "approve", "demo.flow", "0.1.0", "--json"]) == 0
    approve_payload = json.loads(capsys.readouterr().out)
    assert approve_payload["status"] == "approved"

    assert cli_main(["marketplace", "search", "demo.flow", "--json"]) == 0
    search_payload = json.loads(capsys.readouterr().out)
    assert search_payload["count"] == 1

    assert cli_main(["marketplace", "comment", "demo.flow", "0.1.0", "--comment", "useful", "--json"]) == 0
    comment_payload = json.loads(capsys.readouterr().out)
    assert comment_payload["ok"] is True
    assert comment_payload["comment"] == "useful"

    assert cli_main(["marketplace", "comments", "demo.flow", "0.1.0", "--json"]) == 0
    comments_payload = json.loads(capsys.readouterr().out)
    assert comments_payload["count"] == 1
