from __future__ import annotations

import json
from pathlib import Path

from namel3ss.training import resolve_training_config, run_training_job


def _write_app(tmp_path: Path) -> Path:
    app = tmp_path / "app.ai"
    app.write_text(
        'spec is "1.0"\ncapabilities:\n  training\n\nflow "demo":\n  return "ok"\n',
        encoding="utf-8",
    )
    return app


def _write_dataset(path: Path, rows: list[dict[str, object]]) -> Path:
    payload = "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")
    return path


def _config(tmp_path: Path, app: Path, *, dataset: Path, output_name: str, seed: int = 13):
    return resolve_training_config(
        project_root=tmp_path,
        app_path=app,
        config_values=None,
        overrides={
            "model_base": "gpt-3.5-turbo",
            "dataset": dataset.as_posix(),
            "epochs": 3,
            "learning_rate": 2e-5,
            "seed": seed,
            "output_name": output_name,
            "mode": "text",
            "validation_split": 0.25,
            "output_dir": (tmp_path / "models").as_posix(),
            "report_dir": (tmp_path / "docs" / "reports").as_posix(),
        },
    )


def test_training_writes_explainability_report(tmp_path: Path) -> None:
    app = _write_app(tmp_path)
    dataset = _write_dataset(
        tmp_path / "data" / "train.jsonl",
        [
            {"input": "q1", "target": "a1"},
            {"input": "q2", "target": "a2"},
            {"input": "q3", "target": "a3"},
            {"input": "q4", "target": "a4"},
        ],
    )
    first = run_training_job(_config(tmp_path, app, dataset=dataset, output_name="supportbot.faq_model_v2"))
    second = run_training_job(_config(tmp_path, app, dataset=dataset, output_name="supportbot.faq_model_v3"))

    first_path = Path(first.explain_report_path)
    second_path = Path(second.explain_report_path)
    assert first_path.exists()
    assert second_path.exists()

    first_payload = json.loads(first_path.read_text(encoding="utf-8"))
    second_payload = json.loads(second_path.read_text(encoding="utf-8"))

    assert first_payload["schema_version"] == 1
    assert first_payload["stage"] == "training"
    assert first_payload["entry_count"] == 2
    assert first_payload["entries"][0]["event_type"] == "training_start"
    assert first_payload["entries"][1]["event_type"] == "training_finish"
    assert set(first_payload["training_metadata"]["metrics"].keys()) == {"accuracy", "bleu"}
    assert (
        first_payload["training_metadata"]["config_hash"]
        == second_payload["training_metadata"]["config_hash"]
    )
