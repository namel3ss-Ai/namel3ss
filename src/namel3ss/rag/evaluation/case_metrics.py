from __future__ import annotations

from namel3ss.rag.contracts.citation_model import normalize_citation_model
from namel3ss.rag.contracts.retrieval_config_model import normalize_retrieval_config_model
from namel3ss.rag.contracts.retrieval_result_model import normalize_retrieval_result_model
from namel3ss.rag.contracts.value_norms import float_value, int_value, map_value, text_value
from namel3ss.rag.determinism.json_policy import canonical_contract_copy
from namel3ss.rag.evaluation.golden_query_suite import EVAL_CASE_SCHEMA_VERSION


EVAL_CASE_RESULT_SCHEMA_VERSION = "rag.eval_case_result@1"


def normalize_case_results(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    rows: list[dict[str, object]] = []
    for item in value:
        rows.append(normalize_case_result(item))
    rows.sort(key=lambda entry: (str(entry.get("case_id") or ""), int(entry.get("case_index") or 0)))
    for index, row in enumerate(rows, start=1):
        row["case_index"] = index
    return rows


def normalize_case_result(value: object) -> dict[str, object]:
    data = map_value(value)
    counts = normalize_counts(data.get("counts"))
    metrics = normalize_metrics(data.get("metrics"))
    matched = normalize_matched(data.get("matched"))
    expected = map_value(data.get("expected"))
    thresholds = normalize_thresholds(data.get("thresholds"))
    issues = normalize_issue_rows(data.get("issues"))
    passed = is_case_passed(metrics=metrics, thresholds=thresholds, counts=counts, issues=issues, expected=expected)
    return {
        "schema_version": text_value(data.get("schema_version"), default=EVAL_CASE_RESULT_SCHEMA_VERSION)
        or EVAL_CASE_RESULT_SCHEMA_VERSION,
        "case_schema_version": text_value(data.get("case_schema_version"), default=EVAL_CASE_SCHEMA_VERSION)
        or EVAL_CASE_SCHEMA_VERSION,
        "case_id": text_value(data.get("case_id")),
        "case_index": int_value(data.get("case_index"), minimum=1, default=1),
        "query": text_value(data.get("query")),
        "answer_text_hash": text_value(data.get("answer_text_hash")),
        "retrieval_config": normalize_retrieval_config_model(data.get("retrieval_config")),
        "expected": canonical_contract_copy(expected),
        "thresholds": thresholds,
        "counts": counts,
        "matched": matched,
        "metrics": metrics,
        "issues": issues,
        "passed": bool(passed),
    }


def normalize_answer_payload(value: object) -> dict[str, object]:
    data = map_value(value)
    citations = _normalize_citation_rows(data.get("citations"))
    retrieval_results = _normalize_retrieval_rows(data.get("retrieval_results"))
    retrieval_config = normalize_retrieval_config_model(data.get("retrieval_config"))
    return {
        "answer_text": text_value(data.get("answer_text")),
        "citations": citations,
        "retrieval_results": retrieval_results,
        "retrieval_config": retrieval_config,
    }


def evaluate_case_metrics(
    *,
    expected: dict[str, object],
    answer_payload: dict[str, object],
) -> tuple[dict[str, float], dict[str, int], dict[str, list[str]], list[str]]:
    answer_text = text_value(answer_payload.get("answer_text"))
    answer_lower = answer_text.lower()
    answer_len = len(answer_text)
    citations = list(answer_payload.get("citations") or [])
    retrieval_results = list(answer_payload.get("retrieval_results") or [])
    expected_chunk_ids = _string_rows(expected.get("expected_chunk_ids"))
    expected_doc_ids = _string_rows(expected.get("expected_doc_ids"))
    answer_substrings = _string_rows(expected.get("answer_substrings"))
    min_citation_count = int_value(expected.get("min_citation_count"), minimum=0, default=0)

    retrieval_chunk_ids = _ordered_unique([text_value(row.get("chunk_id")) for row in retrieval_results])
    citation_chunk_ids = _ordered_unique([text_value(row.get("chunk_id")) for row in citations])
    retrieval_doc_ids = _ordered_unique([text_value(row.get("doc_id")) for row in retrieval_results])

    expected_chunk_set = set(expected_chunk_ids)
    expected_doc_set = set(expected_doc_ids)
    retrieval_chunk_set = set(retrieval_chunk_ids)
    citation_chunk_set = set(citation_chunk_ids)
    retrieval_doc_set = set(retrieval_doc_ids)

    matched_chunks_retrieval = sorted(expected_chunk_set.intersection(retrieval_chunk_set))
    matched_chunks_citations = sorted(expected_chunk_set.intersection(citation_chunk_set))
    matched_docs_retrieval = sorted(expected_doc_set.intersection(retrieval_doc_set))
    matched_answer_substrings = sorted(
        [substring for substring in answer_substrings if substring.lower() in answer_lower]
    )

    valid_span_count = 0
    grounded_citation_count = 0
    issues: list[str] = []
    for citation in citations:
        citation_id = text_value(citation.get("citation_id"))
        span = map_value(citation.get("answer_span"))
        span_start = int_value(span.get("start_char"), minimum=0, default=0)
        span_end = int_value(span.get("end_char"), minimum=span_start, default=span_start)
        if span_start >= 0 and span_end > span_start and span_end <= answer_len:
            valid_span_count += 1
        else:
            issues.append(f"invalid_answer_span:{citation_id}")
        preview_target = map_value(citation.get("preview_target"))
        target_page = int_value(preview_target.get("page"), minimum=1, default=1)
        chunk_id = text_value(citation.get("chunk_id"))
        if target_page > 0 and chunk_id in retrieval_chunk_set:
            grounded_citation_count += 1
        else:
            issues.append(f"ungrounded_citation:{citation_id}")

    citation_count = len(citations)
    retrieval_recall = _ratio(len(matched_chunks_retrieval), len(expected_chunk_ids))
    citation_recall = _ratio(len(matched_chunks_citations), len(expected_chunk_ids))
    doc_recall = _ratio(len(matched_docs_retrieval), len(expected_doc_ids))
    answer_contains = _ratio(len(matched_answer_substrings), len(answer_substrings))
    citation_grounding = _citation_ratio(
        numerator=grounded_citation_count,
        denominator=citation_count,
        min_citation_count=min_citation_count,
    )
    answer_span_consistency = _citation_ratio(
        numerator=valid_span_count,
        denominator=citation_count,
        min_citation_count=min_citation_count,
    )
    overall_score = _average_metric(
        [
            retrieval_recall,
            citation_recall,
            citation_grounding,
            answer_span_consistency,
            answer_contains,
            doc_recall,
        ]
    )
    counts = {
        "citation_count": citation_count,
        "expected_chunk_count": len(expected_chunk_ids),
        "expected_doc_count": len(expected_doc_ids),
        "expected_substring_count": len(answer_substrings),
        "retrieval_result_count": len(retrieval_results),
    }
    matched = {
        "answer_substrings": matched_answer_substrings,
        "chunks_in_citations": matched_chunks_citations,
        "chunks_in_retrieval": matched_chunks_retrieval,
        "docs_in_retrieval": matched_docs_retrieval,
    }
    metrics = {
        "answer_contains": answer_contains,
        "answer_span_consistency": answer_span_consistency,
        "citation_grounding": citation_grounding,
        "citation_recall": citation_recall,
        "doc_recall": doc_recall,
        "overall_score": overall_score,
        "retrieval_recall": retrieval_recall,
    }
    if citation_count < min_citation_count:
        issues.append("citation_count_below_minimum")
    return normalize_metrics(metrics), normalize_counts(counts), normalize_matched(matched), issues


def normalize_thresholds(value: object) -> dict[str, float]:
    data = map_value(value)
    rows: dict[str, float] = {}
    for key, default in _THRESHOLD_DEFAULTS.items():
        rows[key] = _unit_float(data.get(key), default=default)
    return rows


def normalize_counts(value: object) -> dict[str, int]:
    data = map_value(value)
    return {
        "citation_count": int_value(data.get("citation_count"), minimum=0, default=0),
        "expected_chunk_count": int_value(data.get("expected_chunk_count"), minimum=0, default=0),
        "expected_doc_count": int_value(data.get("expected_doc_count"), minimum=0, default=0),
        "expected_substring_count": int_value(data.get("expected_substring_count"), minimum=0, default=0),
        "retrieval_result_count": int_value(data.get("retrieval_result_count"), minimum=0, default=0),
    }


def normalize_metrics(value: object) -> dict[str, float]:
    data = map_value(value)
    rows: dict[str, float] = {}
    for key in _METRIC_KEYS:
        rows[key] = _unit_float(data.get(key), default=0.0)
    return rows


def normalize_matched(value: object) -> dict[str, list[str]]:
    data = map_value(value)
    return {
        "answer_substrings": _string_rows(data.get("answer_substrings")),
        "chunks_in_citations": _string_rows(data.get("chunks_in_citations")),
        "chunks_in_retrieval": _string_rows(data.get("chunks_in_retrieval")),
        "docs_in_retrieval": _string_rows(data.get("docs_in_retrieval")),
    }


def normalize_issue_rows(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return sorted(set(text_value(item) for item in value if text_value(item)))


def is_case_passed(
    *,
    metrics: dict[str, float],
    thresholds: dict[str, float],
    counts: dict[str, int],
    issues: list[str],
    expected: dict[str, object],
) -> bool:
    if issues:
        return False
    min_citation_count = int_value(expected.get("min_citation_count"), minimum=0, default=0)
    if int(counts.get("citation_count") or 0) < min_citation_count:
        return False
    checks = {
        "retrieval_recall": metrics.get("retrieval_recall", 0.0) >= thresholds.get("min_retrieval_recall", 1.0),
        "citation_recall": metrics.get("citation_recall", 0.0) >= thresholds.get("min_citation_recall", 1.0),
        "citation_grounding": metrics.get("citation_grounding", 0.0) >= thresholds.get("min_citation_grounding", 1.0),
        "answer_span_consistency": metrics.get("answer_span_consistency", 0.0)
        >= thresholds.get("min_answer_span_consistency", 1.0),
        "answer_contains": metrics.get("answer_contains", 0.0) >= thresholds.get("min_answer_contains", 1.0),
        "overall_score": metrics.get("overall_score", 0.0) >= thresholds.get("min_overall_score", 1.0),
    }
    return all(checks.values())


def _normalize_citation_rows(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    rows = [normalize_citation_model(item) for item in value]
    rows.sort(key=lambda entry: (int(entry.get("mention_index") or 0), text_value(entry.get("citation_id"))))
    return rows


def _normalize_retrieval_rows(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    rows = [normalize_retrieval_result_model(item) for item in value]
    rows.sort(key=lambda entry: (int(entry.get("rank") or 0), text_value(entry.get("chunk_id"))))
    return rows


def _ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 1.0
    return float_value(float(numerator) / float(denominator), default=0.0, precision=6)


def _citation_ratio(*, numerator: int, denominator: int, min_citation_count: int) -> float:
    if denominator <= 0:
        return 1.0 if min_citation_count == 0 else 0.0
    return float_value(float(numerator) / float(denominator), default=0.0, precision=6)


def _average_metric(values: list[float]) -> float:
    if not values:
        return 0.0
    return float_value(sum(values) / float(len(values)), default=0.0, precision=6)


def _ordered_unique(rows: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for item in rows:
        token = text_value(item)
        if not token or token in seen:
            continue
        seen.add(token)
        output.append(token)
    return output


def _string_rows(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return sorted(set(text_value(item) for item in value if text_value(item)))


def _unit_float(value: object, *, default: float) -> float:
    number = float_value(value, default=default, precision=6)
    if number < 0:
        return 0.0
    if number > 1:
        return 1.0
    return number


_THRESHOLD_DEFAULTS = {
    "min_answer_contains": 1.0,
    "min_answer_span_consistency": 1.0,
    "min_citation_grounding": 1.0,
    "min_citation_recall": 1.0,
    "min_overall_score": 1.0,
    "min_retrieval_recall": 1.0,
}

_METRIC_KEYS = [
    "answer_contains",
    "answer_span_consistency",
    "citation_grounding",
    "citation_recall",
    "doc_recall",
    "overall_score",
    "retrieval_recall",
]


__all__ = [
    "EVAL_CASE_RESULT_SCHEMA_VERSION",
    "evaluate_case_metrics",
    "is_case_passed",
    "normalize_answer_payload",
    "normalize_case_result",
    "normalize_case_results",
    "normalize_counts",
    "normalize_issue_rows",
    "normalize_matched",
    "normalize_metrics",
    "normalize_thresholds",
]
