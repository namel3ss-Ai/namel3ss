from __future__ import annotations

import json
from pathlib import Path

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.models import load_model_registry
from namel3ss.training import resolve_training_config, run_training_job


def _write_app(tmp_path: Path, *, with_training_capability: bool = True) -> Path:
    capabilities = "\ncapabilities:\n  training\n" if with_training_capability else ""
    app = tmp_path / "app.ai"
    app.write_text(
        f'spec is "1.0"\n{capabilities}\nflow "demo":\n  return "ok"\n',
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


def test_training_runner_is_deterministic_for_same_seed_and_dataset(tmp_path: Path) -> None:
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

    assert first.artifact_checksum == second.artifact_checksum
    assert first.metrics == second.metrics
    assert first.dataset_snapshot["content_hash"] == second.dataset_snapshot["content_hash"]
    assert set(first.metrics.keys()) == {"accuracy", "bleu"}

    registry = load_model_registry(tmp_path, app)
    assert registry.find("supportbot.faq_model_v2") is not None
    assert registry.find("supportbot.faq_model_v3") is not None


def test_training_runner_rejects_duplicate_output_name(tmp_path: Path) -> None:
    app = _write_app(tmp_path)
    dataset = _write_dataset(
        tmp_path / "data" / "train.jsonl",
        [
            {"input": "q1", "target": "a1"},
            {"input": "q2", "target": "a2"},
        ],
    )

    config = _config(tmp_path, app, dataset=dataset, output_name="supportbot.faq_model_v1")
    run_training_job(config)

    with pytest.raises(Namel3ssError, match="already exists"):
        run_training_job(config)


def test_training_runner_requires_multiple_rows_for_split(tmp_path: Path) -> None:
    app = _write_app(tmp_path)
    dataset = _write_dataset(tmp_path / "data" / "train.jsonl", [{"input": "q1", "target": "a1"}])

    with pytest.raises(Namel3ssError, match="at least 2"):
        run_training_job(_config(tmp_path, app, dataset=dataset, output_name="supportbot.faq_model_v1"))
