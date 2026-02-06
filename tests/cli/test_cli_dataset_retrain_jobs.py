from __future__ import annotations

import json
from pathlib import Path

from namel3ss.cli.main import main as cli_main
from namel3ss.feedback import append_feedback_entry
from namel3ss.observability.ai_metrics import record_ai_metric


def _write_app(tmp_path: Path) -> Path:
    app = tmp_path / "app.ai"
    app.write_text('spec is "1.0"\n\nflow "ask_ai":\n  return "ok"\n', encoding="utf-8")
    return app


def _write_models_config(tmp_path: Path) -> None:
    models = tmp_path / ".namel3ss" / "models.yaml"
    models.parent.mkdir(parents=True, exist_ok=True)
    models.write_text(
        "models:\n"
        "  base:\n"
        "    version: 1.0\n"
        "    image: repo/base:1\n",
        encoding="utf-8",
    )


def test_cli_dataset_and_retrain_job_lifecycle(tmp_path: Path, capsys, monkeypatch) -> None:
    app = _write_app(tmp_path)
    _write_models_config(tmp_path)
    registry_file = tmp_path / "registry_ops.json"
    (tmp_path / "mlops.yaml").write_text(
        f"tool: mlflow\nregistry_url: {registry_file.as_uri()}\nproject_name: demo\ntraining_backends:\n  - huggingface\n",
        encoding="utf-8",
    )
    (tmp_path / "retrain.yaml").write_text(
        "min_positive_ratio: 0.95\n"
        "min_accuracy: 0.95\n"
        "min_completion_quality: 0.95\n"
        "min_f1: 0.95\n"
        "max_drift: 0.05\n"
        "negative_feedback_count: 1\n"
        "threshold_window: 10\n"
        "schedule: daily\n",
        encoding="utf-8",
    )

    append_feedback_entry(tmp_path, app, flow_name="ask_ai", input_id="in_1", rating="bad")
    record_ai_metric(
        project_root=tmp_path,
        app_path=app,
        record={
            "flow_name": "ask_ai",
            "input_id": "in_1",
            "accuracy": 0.0,
            "latency_steps": 2,
            "output": "x",
        },
    )

    monkeypatch.chdir(tmp_path)

    assert (
        cli_main(
            [
                "dataset",
                "add-version",
                "faq-dataset",
                "1.0.0",
                "--source",
                "faq_upload_2026_01",
                "--schema",
                "question:text,answer:text",
                "--transform",
                "removed empty answers",
                "--json",
            ]
        )
        == 0
    )
    added = json.loads(capsys.readouterr().out)
    assert added["ok"] is True
    assert added["dataset_name"] == "faq-dataset"

    assert cli_main(["dataset", "list", "--json"]) == 0
    listed = json.loads(capsys.readouterr().out)
    assert listed["count"] == 1
    assert listed["datasets"][0]["latest_version"] == "1.0.0"

    assert cli_main(["dataset", "history", "faq-dataset", "--json"]) == 0
    history = json.loads(capsys.readouterr().out)
    assert history["count"] == 1
    assert history["versions"][0]["source"] == "faq_upload_2026_01"

    assert cli_main(["retrain", "schedule", "--json"]) == 0
    scheduled = json.loads(capsys.readouterr().out)
    assert scheduled["ok"] is True
    assert scheduled["scheduled_count"] >= 1
    assert scheduled["backend"] == "huggingface"
    job_id = scheduled["jobs"][0]["job_id"]

    assert cli_main(["retrain", "list", "--json"]) == 0
    jobs = json.loads(capsys.readouterr().out)
    assert jobs["count"] >= 1
    assert jobs["jobs"][0]["status"] in {"pending", "completed"}

    assert cli_main(["retrain", "run", job_id, "--json"]) == 0
    run_payload = json.loads(capsys.readouterr().out)
    assert run_payload["ok"] is True
    assert run_payload["job"]["status"] == "completed"
    assert str(run_payload["job"]["result_uri"]).startswith("training://")
