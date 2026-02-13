from __future__ import annotations

from namel3ss.rag.contracts.value_norms import float_value, map_value, merge_extensions, text_value
from namel3ss.rag.evaluation.eval_runner import normalize_eval_run_model


EVAL_REGRESSION_SCHEMA_VERSION = "rag.eval_regression@1"


def build_regression_report(
    *,
    current_run: object,
    baseline_run: object | None = None,
    thresholds: object = None,
    schema_version: str = EVAL_REGRESSION_SCHEMA_VERSION,
    extensions: dict[str, object] | None = None,
) -> dict[str, object]:
    current = normalize_eval_run_model(current_run)
    baseline = normalize_eval_run_model(baseline_run) if baseline_run is not None else None
    threshold_rows = normalize_regression_thresholds(thresholds)
    current_summary = _summary_rows(current)
    baseline_summary = _summary_rows(baseline) if baseline is not None else _empty_summary()
    gates = _build_minimum_gates(current_summary=current_summary, thresholds=threshold_rows)
    if baseline is not None:
        gates.extend(
            _build_drop_gates(
                current_summary=current_summary,
                baseline_summary=baseline_summary,
                thresholds=threshold_rows,
            )
        )
    gates.sort(key=lambda item: str(item.get("gate_id") or ""))
    passed = all(bool(item.get("passed")) for item in gates)
    return {
        "schema_version": text_value(schema_version, default=EVAL_REGRESSION_SCHEMA_VERSION) or EVAL_REGRESSION_SCHEMA_VERSION,
        "status": "pass" if passed else "fail",
        "passed": passed,
        "current_run_fingerprint": text_value(current.get("run_determinism_fingerprint")),
        "baseline_run_fingerprint": text_value(baseline.get("run_determinism_fingerprint")) if baseline is not None else "",
        "thresholds": threshold_rows,
        "gates": gates,
        "current_summary": current_summary,
        "baseline_summary": baseline_summary,
        "metric_deltas": _metric_deltas(current_summary=current_summary, baseline_summary=baseline_summary),
        "extensions": merge_extensions(extensions),
    }


def normalize_regression_report(value: object) -> dict[str, object]:
    data = map_value(value)
    threshold_rows = normalize_regression_thresholds(data.get("thresholds"))
    current_summary = _normalize_summary(data.get("current_summary"))
    baseline_summary = _normalize_summary(data.get("baseline_summary"))
    gates = _normalize_gate_rows(data.get("gates"))
    passed = bool(data.get("passed"))
    if not gates:
        gates = _build_minimum_gates(current_summary=current_summary, thresholds=threshold_rows)
        gates.sort(key=lambda item: str(item.get("gate_id") or ""))
        passed = all(bool(item.get("passed")) for item in gates)
    return {
        "schema_version": text_value(data.get("schema_version"), default=EVAL_REGRESSION_SCHEMA_VERSION)
        or EVAL_REGRESSION_SCHEMA_VERSION,
        "status": "pass" if passed else "fail",
        "passed": passed,
        "current_run_fingerprint": text_value(data.get("current_run_fingerprint")),
        "baseline_run_fingerprint": text_value(data.get("baseline_run_fingerprint")),
        "thresholds": threshold_rows,
        "gates": gates,
        "current_summary": current_summary,
        "baseline_summary": baseline_summary,
        "metric_deltas": _metric_deltas(current_summary=current_summary, baseline_summary=baseline_summary),
        "extensions": merge_extensions(data.get("extensions")),
    }


def normalize_regression_thresholds(value: object) -> dict[str, float]:
    data = map_value(value)
    rows: dict[str, float] = {}
    for key, default in _THRESHOLD_DEFAULTS.items():
        rows[key] = _unit_float(data.get(key), default=default)
    return rows


def regression_gate_passed(report: object) -> bool:
    normalized = normalize_regression_report(report)
    return bool(normalized.get("passed"))


def raise_on_regression_failure(report: object) -> None:
    normalized = normalize_regression_report(report)
    if bool(normalized.get("passed")):
        return
    failed = [row for row in normalized.get("gates") or [] if not bool(row.get("passed"))]
    gate_ids = ", ".join(str(row.get("gate_id") or "") for row in failed)
    message = "RAG regression gate failed"
    if gate_ids:
        message = f"{message}: {gate_ids}"
    raise RuntimeError(message)


def _build_minimum_gates(*, current_summary: dict[str, float], thresholds: dict[str, float]) -> list[dict[str, object]]:
    rows = [
        _minimum_gate(
            gate_id="pass_rate.min",
            actual=current_summary.get("pass_rate", 0.0),
            required=thresholds.get("min_pass_rate", 1.0),
        ),
        _minimum_gate(
            gate_id="avg_retrieval_recall.min",
            actual=current_summary.get("avg_retrieval_recall", 0.0),
            required=thresholds.get("min_avg_retrieval_recall", 1.0),
        ),
        _minimum_gate(
            gate_id="avg_citation_recall.min",
            actual=current_summary.get("avg_citation_recall", 0.0),
            required=thresholds.get("min_avg_citation_recall", 1.0),
        ),
        _minimum_gate(
            gate_id="avg_citation_grounding.min",
            actual=current_summary.get("avg_citation_grounding", 0.0),
            required=thresholds.get("min_avg_citation_grounding", 1.0),
        ),
        _minimum_gate(
            gate_id="avg_answer_span_consistency.min",
            actual=current_summary.get("avg_answer_span_consistency", 0.0),
            required=thresholds.get("min_avg_answer_span_consistency", 1.0),
        ),
        _minimum_gate(
            gate_id="avg_answer_contains.min",
            actual=current_summary.get("avg_answer_contains", 0.0),
            required=thresholds.get("min_avg_answer_contains", 1.0),
        ),
        _minimum_gate(
            gate_id="avg_overall_score.min",
            actual=current_summary.get("avg_overall_score", 0.0),
            required=thresholds.get("min_avg_overall_score", 1.0),
        ),
    ]
    return rows


def _build_drop_gates(
    *,
    current_summary: dict[str, float],
    baseline_summary: dict[str, float],
    thresholds: dict[str, float],
) -> list[dict[str, object]]:
    pass_rate_drop = _non_negative(baseline_summary.get("pass_rate", 0.0) - current_summary.get("pass_rate", 0.0))
    overall_drop = _non_negative(
        baseline_summary.get("avg_overall_score", 0.0) - current_summary.get("avg_overall_score", 0.0)
    )
    grounding_drop = _non_negative(
        baseline_summary.get("avg_citation_grounding", 0.0) - current_summary.get("avg_citation_grounding", 0.0)
    )
    return [
        _maximum_gate(
            gate_id="pass_rate.drop_max",
            actual=pass_rate_drop,
            allowed=thresholds.get("max_pass_rate_drop", 0.0),
        ),
        _maximum_gate(
            gate_id="avg_overall_score.drop_max",
            actual=overall_drop,
            allowed=thresholds.get("max_avg_overall_score_drop", 0.0),
        ),
        _maximum_gate(
            gate_id="avg_citation_grounding.drop_max",
            actual=grounding_drop,
            allowed=thresholds.get("max_avg_citation_grounding_drop", 0.0),
        ),
    ]


def _minimum_gate(*, gate_id: str, actual: float, required: float) -> dict[str, object]:
    actual_value = _unit_float(actual, default=0.0)
    required_value = _unit_float(required, default=1.0)
    return {
        "gate_id": gate_id,
        "operator": "gte",
        "actual": actual_value,
        "required": required_value,
        "passed": actual_value >= required_value,
    }


def _maximum_gate(*, gate_id: str, actual: float, allowed: float) -> dict[str, object]:
    actual_value = _unit_float(actual, default=0.0)
    allowed_value = _unit_float(allowed, default=0.0)
    return {
        "gate_id": gate_id,
        "operator": "lte",
        "actual": actual_value,
        "required": allowed_value,
        "passed": actual_value <= allowed_value,
    }


def _summary_rows(run: dict[str, object] | None) -> dict[str, float]:
    if not isinstance(run, dict):
        return _empty_summary()
    return _normalize_summary(run.get("summary"))


def _normalize_summary(value: object) -> dict[str, float]:
    data = map_value(value)
    rows: dict[str, float] = {}
    for key in _SUMMARY_KEYS:
        rows[key] = _unit_float(data.get(key), default=0.0)
    return rows


def _normalize_gate_rows(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    rows: list[dict[str, object]] = []
    for item in value:
        data = map_value(item)
        rows.append(
            {
                "gate_id": text_value(data.get("gate_id")),
                "operator": text_value(data.get("operator"), default="gte") or "gte",
                "actual": _unit_float(data.get("actual"), default=0.0),
                "required": _unit_float(data.get("required"), default=0.0),
                "passed": bool(data.get("passed")),
            }
        )
    rows.sort(key=lambda entry: str(entry.get("gate_id") or ""))
    return rows


def _metric_deltas(*, current_summary: dict[str, float], baseline_summary: dict[str, float]) -> dict[str, float]:
    rows: dict[str, float] = {}
    for key in _SUMMARY_KEYS:
        rows[f"{key}_delta"] = _signed_unit_float(
            current_summary.get(key, 0.0) - baseline_summary.get(key, 0.0),
            default=0.0,
        )
    return rows


def _empty_summary() -> dict[str, float]:
    return {key: 0.0 for key in _SUMMARY_KEYS}


def _unit_float(value: object, *, default: float) -> float:
    number = float_value(value, default=default, precision=6)
    if number < 0:
        return 0.0
    if number > 1:
        return 1.0
    return number


def _signed_unit_float(value: object, *, default: float) -> float:
    number = float_value(value, default=default, precision=6)
    if number < -1:
        return -1.0
    if number > 1:
        return 1.0
    return number


def _non_negative(value: object) -> float:
    number = float_value(value, default=0.0, precision=6)
    if number < 0:
        return 0.0
    return number


_SUMMARY_KEYS = [
    "pass_rate",
    "avg_retrieval_recall",
    "avg_citation_recall",
    "avg_citation_grounding",
    "avg_answer_span_consistency",
    "avg_answer_contains",
    "avg_overall_score",
]

_THRESHOLD_DEFAULTS = {
    "min_pass_rate": 1.0,
    "min_avg_retrieval_recall": 1.0,
    "min_avg_citation_recall": 1.0,
    "min_avg_citation_grounding": 1.0,
    "min_avg_answer_span_consistency": 1.0,
    "min_avg_answer_contains": 1.0,
    "min_avg_overall_score": 1.0,
    "max_pass_rate_drop": 0.0,
    "max_avg_overall_score_drop": 0.0,
    "max_avg_citation_grounding_drop": 0.0,
}


__all__ = [
    "EVAL_REGRESSION_SCHEMA_VERSION",
    "build_regression_report",
    "normalize_regression_report",
    "normalize_regression_thresholds",
    "raise_on_regression_failure",
    "regression_gate_passed",
]
