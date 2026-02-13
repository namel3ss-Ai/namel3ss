from __future__ import annotations

import hashlib
from collections.abc import Callable

from namel3ss.rag.contracts.value_norms import float_value, int_value, map_value, merge_extensions, text_value
from namel3ss.rag.determinism.json_policy import canonical_contract_copy, canonical_contract_hash
from namel3ss.rag.evaluation.case_metrics import (
    EVAL_CASE_RESULT_SCHEMA_VERSION,
    evaluate_case_metrics,
    is_case_passed,
    normalize_answer_payload,
    normalize_case_results,
    normalize_metrics,
    normalize_thresholds,
)
from namel3ss.rag.evaluation.golden_query_suite import (
    EVAL_CASE_SCHEMA_VERSION,
    EVAL_SUITE_SCHEMA_VERSION,
    normalize_eval_case_model,
    normalize_golden_query_suite,
)


EVAL_RUN_SCHEMA_VERSION = "rag.eval_run@1"


def run_eval_suite(
    *,
    suite: object,
    answer_runner: Callable[[dict[str, object]], dict[str, object]],
    run_label: str = "",
    schema_version: str = EVAL_RUN_SCHEMA_VERSION,
    extensions: dict[str, object] | None = None,
) -> dict[str, object]:
    suite_value = normalize_golden_query_suite(suite)
    case_rows = list(suite_value.get("cases") or [])
    case_results: list[dict[str, object]] = []
    for index, case_value in enumerate(case_rows, start=1):
        case = normalize_eval_case_model(case_value)
        case_results.append(_run_eval_case(case=case, answer_runner=answer_runner, case_index=index))
    summary = _build_run_summary(case_results)
    fingerprint = _build_run_fingerprint(
        suite_id=text_value(suite_value.get("suite_id")),
        case_results=case_results,
        summary=summary,
    )
    return {
        "schema_version": text_value(schema_version, default=EVAL_RUN_SCHEMA_VERSION) or EVAL_RUN_SCHEMA_VERSION,
        "suite_schema_version": text_value(suite_value.get("schema_version"), default=EVAL_SUITE_SCHEMA_VERSION)
        or EVAL_SUITE_SCHEMA_VERSION,
        "suite_id": text_value(suite_value.get("suite_id")),
        "suite_name": text_value(suite_value.get("name")),
        "run_label": text_value(run_label),
        "run_determinism_fingerprint": fingerprint,
        "case_results": case_results,
        "summary": summary,
        "extensions": merge_extensions(extensions),
    }


def normalize_eval_run_model(value: object) -> dict[str, object]:
    data = map_value(value)
    case_rows = normalize_case_results(data.get("case_results"))
    summary = _normalize_run_summary(data.get("summary"), case_rows=case_rows)
    suite_id = text_value(data.get("suite_id"))
    fingerprint = text_value(data.get("run_determinism_fingerprint")) or _build_run_fingerprint(
        suite_id=suite_id,
        case_results=case_rows,
        summary=summary,
    )
    return {
        "schema_version": text_value(data.get("schema_version"), default=EVAL_RUN_SCHEMA_VERSION) or EVAL_RUN_SCHEMA_VERSION,
        "suite_schema_version": text_value(data.get("suite_schema_version"), default=EVAL_SUITE_SCHEMA_VERSION)
        or EVAL_SUITE_SCHEMA_VERSION,
        "suite_id": suite_id,
        "suite_name": text_value(data.get("suite_name")),
        "run_label": text_value(data.get("run_label")),
        "run_determinism_fingerprint": fingerprint,
        "case_results": case_rows,
        "summary": summary,
        "extensions": merge_extensions(data.get("extensions")),
    }


def _run_eval_case(
    *,
    case: dict[str, object],
    answer_runner: Callable[[dict[str, object]], dict[str, object]],
    case_index: int,
) -> dict[str, object]:
    expected = map_value(case.get("expected"))
    thresholds = normalize_thresholds(case.get("thresholds"))
    runner_error = ""
    answer_payload: dict[str, object]
    try:
        answer_output = answer_runner(canonical_contract_copy(case))
        answer_payload = map_value(answer_output)
    except Exception as exc:
        answer_payload = {}
        runner_error = str(exc)
    normalized_answer = normalize_answer_payload(answer_payload)
    metrics, counts, matched, issues = evaluate_case_metrics(expected=expected, answer_payload=normalized_answer)
    if runner_error:
        issues.append(f"runner_error:{runner_error}")
    issues = sorted(set(item for item in issues if item))
    passed = is_case_passed(metrics=metrics, thresholds=thresholds, counts=counts, issues=issues, expected=expected)
    answer_text_hash = hashlib.sha256(text_value(normalized_answer.get("answer_text")).encode("utf-8")).hexdigest()
    return {
        "schema_version": EVAL_CASE_RESULT_SCHEMA_VERSION,
        "case_schema_version": text_value(case.get("schema_version"), default=EVAL_CASE_SCHEMA_VERSION) or EVAL_CASE_SCHEMA_VERSION,
        "case_id": text_value(case.get("case_id")),
        "case_index": int_value(case_index, minimum=1, default=1),
        "query": text_value(case.get("query")),
        "answer_text_hash": answer_text_hash,
        "retrieval_config": canonical_contract_copy(normalized_answer.get("retrieval_config")),
        "expected": canonical_contract_copy(expected),
        "thresholds": thresholds,
        "counts": counts,
        "matched": matched,
        "metrics": metrics,
        "issues": issues,
        "passed": bool(passed),
    }


def _build_run_summary(case_results: list[dict[str, object]]) -> dict[str, float | int]:
    case_count = len(case_results)
    passed_count = sum(1 for row in case_results if bool(row.get("passed")))
    failed_count = case_count - passed_count
    metrics = [normalize_metrics(row.get("metrics")) for row in case_results]
    return {
        "avg_answer_contains": _average_metric([float(entry.get("answer_contains") or 0) for entry in metrics]),
        "avg_answer_span_consistency": _average_metric([float(entry.get("answer_span_consistency") or 0) for entry in metrics]),
        "avg_citation_grounding": _average_metric([float(entry.get("citation_grounding") or 0) for entry in metrics]),
        "avg_citation_recall": _average_metric([float(entry.get("citation_recall") or 0) for entry in metrics]),
        "avg_doc_recall": _average_metric([float(entry.get("doc_recall") or 0) for entry in metrics]),
        "avg_overall_score": _average_metric([float(entry.get("overall_score") or 0) for entry in metrics]),
        "avg_retrieval_recall": _average_metric([float(entry.get("retrieval_recall") or 0) for entry in metrics]),
        "case_count": case_count,
        "failed_count": failed_count,
        "pass_rate": _ratio(passed_count, case_count),
        "passed_count": passed_count,
    }


def _normalize_run_summary(value: object, *, case_rows: list[dict[str, object]]) -> dict[str, float | int]:
    data = map_value(value)
    fallback = _build_run_summary(case_rows)
    summary: dict[str, float | int] = {}
    for key, fallback_value in fallback.items():
        if isinstance(fallback_value, int):
            summary[key] = int_value(data.get(key), minimum=0, default=fallback_value)
        else:
            summary[key] = _unit_float(data.get(key), default=float(fallback_value))
    case_count = int(summary.get("case_count") or 0)
    passed_count = int(summary.get("passed_count") or 0)
    if passed_count > case_count:
        passed_count = case_count
        summary["passed_count"] = passed_count
    summary["failed_count"] = max(0, case_count - passed_count)
    summary["pass_rate"] = _ratio(passed_count, case_count)
    return summary


def _build_run_fingerprint(
    *,
    suite_id: str,
    case_results: list[dict[str, object]],
    summary: dict[str, object],
) -> str:
    payload = {
        "case_results": [
            {
                "case_id": text_value(row.get("case_id")),
                "metrics": normalize_metrics(row.get("metrics")),
                "passed": bool(row.get("passed")),
            }
            for row in case_results
        ],
        "suite_id": suite_id,
        "summary": map_value(summary),
    }
    digest = canonical_contract_hash(payload)
    return f"evalrun_{digest[:20]}"


def _ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 1.0
    return float_value(float(numerator) / float(denominator), default=0.0, precision=6)


def _average_metric(values: list[float]) -> float:
    if not values:
        return 0.0
    return float_value(sum(values) / float(len(values)), default=0.0, precision=6)


def _unit_float(value: object, *, default: float) -> float:
    number = float_value(value, default=default, precision=6)
    if number < 0:
        return 0.0
    if number > 1:
        return 1.0
    return number


__all__ = [
    "EVAL_CASE_RESULT_SCHEMA_VERSION",
    "EVAL_RUN_SCHEMA_VERSION",
    "normalize_eval_run_model",
    "run_eval_suite",
]
