from __future__ import annotations

from namel3ss.observability.ai_metrics import (
    apply_thresholds,
    build_ai_record,
    load_ai_metrics,
    load_thresholds,
    record_ai_metric,
    summarize_ai_metrics,
    thresholds_path,
)


def test_ai_metrics_record_and_thresholds(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("N3_PERSIST_ROOT", str(tmp_path))
    record = build_ai_record(
        flow_name="classify_ticket",
        kind="classification",
        input_text="hello",
        output_text="spam",
        expected="spam",
        accuracy=1.0,
        latency_steps=2,
        prompt_tokens=5,
        completion_tokens=7,
    )
    record_ai_metric(project_root=None, app_path=None, record=record)
    records = load_ai_metrics(None, None)
    assert records == [record]
    summary = summarize_ai_metrics(records)
    assert summary == {
        "total_calls": 1,
        "classification_accuracy": 1.0,
        "latency_steps_avg": 2.0,
        "prompt_tokens_avg": 5.0,
        "completion_tokens_avg": 7.0,
    }
    path = thresholds_path(None, None)
    assert path is not None
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('{"classification_accuracy": 0.9}', encoding="utf-8")
    thresholds = load_thresholds(None, None)
    assert thresholds == {"classification_accuracy": 0.9}
    drift = apply_thresholds(summary, thresholds)
    assert drift == [
        {
            "metric": "classification_accuracy",
            "value": 1.0,
            "threshold": 0.9,
            "drifted": False,
        }
    ]
