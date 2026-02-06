from __future__ import annotations

from pathlib import Path

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.feedback import append_feedback_entry
from namel3ss.observability.ai_metrics import record_ai_metric
from namel3ss.retrain import build_retrain_payload, write_retrain_payload



def _write_app(tmp_path: Path) -> Path:
    app = tmp_path / "app.ai"
    app.write_text('spec is "1.0"\n\nflow "ask_ai":\n  return "ok"\n', encoding="utf-8")
    return app



def _write_models(tmp_path: Path) -> None:
    models = tmp_path / ".namel3ss" / "models.yaml"
    models.parent.mkdir(parents=True, exist_ok=True)
    models.write_text(
        "models:\n"
        "  base:\n"
        "    version: 1.0\n"
        "    image: repo/base:1\n",
        encoding="utf-8",
    )



def test_retrain_payload_schedules_suggestions(tmp_path: Path) -> None:
    app = _write_app(tmp_path)
    _write_models(tmp_path)
    (tmp_path / "feedback.yaml").write_text(
        "min_positive_ratio: 0.8\n"
        "min_accuracy: 0.9\n"
        "min_completion_quality: 0.9\n",
        encoding="utf-8",
    )

    append_feedback_entry(app.parent, app, flow_name="ask_ai", input_id="i1", rating="bad")
    record_ai_metric(
        project_root=app.parent,
        app_path=app,
        record={
            "flow_name": "ask_ai",
            "input_id": "i1",
            "accuracy": 0.0,
            "latency_steps": 2,
            "output": "x",
        },
    )

    payload = build_retrain_payload(app.parent, app)
    suggestions = payload.get("suggestions") or []
    assert suggestions
    assert suggestions[0]["model_name"] == "base"

    out_path = write_retrain_payload(app.parent, app)
    assert out_path.exists()



def test_retrain_thresholds_reject_unknown_keys(tmp_path: Path) -> None:
    app = _write_app(tmp_path)
    (tmp_path / "feedback.yaml").write_text("unknown_key: 1\n", encoding="utf-8")
    with pytest.raises(Namel3ssError):
        build_retrain_payload(app.parent, app)


def test_retrain_yaml_supports_drift_and_f1_thresholds(tmp_path: Path) -> None:
    app = _write_app(tmp_path)
    _write_models(tmp_path)
    (tmp_path / "retrain.yaml").write_text(
        "min_positive_ratio: 0.8\n"
        "min_accuracy: 0.9\n"
        "min_completion_quality: 0.9\n"
        "min_f1: 0.95\n"
        "max_drift: 0.1\n"
        "negative_feedback_count: 1\n"
        "threshold_window: 10\n"
        "schedule: daily\n",
        encoding="utf-8",
    )
    append_feedback_entry(app.parent, app, flow_name="ask_ai", input_id="i1", rating="bad")
    record_ai_metric(
        project_root=app.parent,
        app_path=app,
        record={
            "flow_name": "ask_ai",
            "input_id": "i1",
            "accuracy": 0.1,
            "latency_steps": 2,
            "output": "x",
        },
    )

    payload = build_retrain_payload(app.parent, app)
    checks = payload.get("thresholds")
    assert isinstance(checks, dict)
    assert "min_f1" in checks
    assert "max_drift" in checks
    assert "negative_feedback_count" in checks
