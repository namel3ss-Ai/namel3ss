from __future__ import annotations

from namel3ss.rag.contracts.retrieval_config_model import (
    RETRIEVAL_CONFIG_SCHEMA_VERSION,
    build_retrieval_config_model,
    normalize_retrieval_config_model,
)
from namel3ss.rag.contracts.value_norms import (
    float_value,
    int_value,
    map_value,
    merge_extensions,
    sorted_string_list,
    text_value,
    unknown_extensions,
)
from namel3ss.rag.determinism.json_policy import canonical_contract_hash


EVAL_CASE_SCHEMA_VERSION = "rag.eval_case@1"
EVAL_SUITE_SCHEMA_VERSION = "rag.eval_suite@1"


def build_eval_case_model(
    *,
    query: str,
    case_id: str | None = None,
    expected: object = None,
    retrieval_config: object = None,
    thresholds: object = None,
    tags: object = None,
    schema_version: str = EVAL_CASE_SCHEMA_VERSION,
    extensions: dict[str, object] | None = None,
) -> dict[str, object]:
    expected_value = _normalize_expected(expected)
    retrieval_config_value = _normalize_retrieval_config(retrieval_config)
    thresholds_value = _normalize_thresholds(thresholds)
    case_id_value = text_value(case_id) or _build_case_id(
        query=text_value(query),
        expected=expected_value,
        retrieval_config=retrieval_config_value,
    )
    return {
        "schema_version": text_value(schema_version, default=EVAL_CASE_SCHEMA_VERSION) or EVAL_CASE_SCHEMA_VERSION,
        "case_id": case_id_value,
        "query": text_value(query),
        "expected": expected_value,
        "retrieval_config": retrieval_config_value,
        "thresholds": thresholds_value,
        "tags": sorted_string_list(tags),
        "extensions": merge_extensions(extensions),
    }


def normalize_eval_case_model(value: object) -> dict[str, object]:
    data = map_value(value)
    expected_value = _normalize_expected(data.get("expected"))
    retrieval_config_value = _normalize_retrieval_config(data.get("retrieval_config"))
    thresholds_value = _normalize_thresholds(data.get("thresholds"))
    case_id_value = text_value(data.get("case_id")) or _build_case_id(
        query=text_value(data.get("query")),
        expected=expected_value,
        retrieval_config=retrieval_config_value,
    )
    extensions = merge_extensions(
        map_value(data.get("extensions")),
        unknown_extensions(data, known_keys=_CASE_FIELDS),
    )
    return {
        "schema_version": text_value(data.get("schema_version"), default=EVAL_CASE_SCHEMA_VERSION) or EVAL_CASE_SCHEMA_VERSION,
        "case_id": case_id_value,
        "query": text_value(data.get("query")),
        "expected": expected_value,
        "retrieval_config": retrieval_config_value,
        "thresholds": thresholds_value,
        "tags": sorted_string_list(data.get("tags")),
        "extensions": extensions,
    }


def build_golden_query_suite(
    *,
    name: str,
    cases: object,
    suite_id: str | None = None,
    schema_version: str = EVAL_SUITE_SCHEMA_VERSION,
    extensions: dict[str, object] | None = None,
) -> dict[str, object]:
    case_rows = _normalize_case_rows(cases)
    suite_id_value = text_value(suite_id) or _build_suite_id(name=text_value(name), cases=case_rows)
    return {
        "schema_version": text_value(schema_version, default=EVAL_SUITE_SCHEMA_VERSION) or EVAL_SUITE_SCHEMA_VERSION,
        "suite_id": suite_id_value,
        "name": text_value(name),
        "cases": case_rows,
        "extensions": merge_extensions(extensions),
    }


def normalize_golden_query_suite(value: object) -> dict[str, object]:
    data = map_value(value)
    case_rows = _normalize_case_rows(data.get("cases"))
    suite_name = text_value(data.get("name"))
    suite_id_value = text_value(data.get("suite_id")) or _build_suite_id(name=suite_name, cases=case_rows)
    extensions = merge_extensions(
        map_value(data.get("extensions")),
        unknown_extensions(data, known_keys=_SUITE_FIELDS),
    )
    return {
        "schema_version": text_value(data.get("schema_version"), default=EVAL_SUITE_SCHEMA_VERSION) or EVAL_SUITE_SCHEMA_VERSION,
        "suite_id": suite_id_value,
        "name": suite_name,
        "cases": case_rows,
        "extensions": extensions,
    }


def _normalize_expected(value: object) -> dict[str, object]:
    data = map_value(value)
    expected_chunk_ids = sorted_string_list(data.get("expected_chunk_ids"))
    expected_doc_ids = sorted_string_list(data.get("expected_doc_ids"))
    answer_substrings = sorted_string_list(data.get("answer_substrings"))
    min_citation_default = 1 if expected_chunk_ids else 0
    min_citation_count = int_value(
        data.get("min_citation_count"),
        default=min_citation_default,
        minimum=0,
    )
    return {
        "answer_substrings": answer_substrings,
        "expected_chunk_ids": expected_chunk_ids,
        "expected_doc_ids": expected_doc_ids,
        "min_citation_count": min_citation_count,
    }


def _normalize_retrieval_config(value: object) -> dict[str, object]:
    if value is None:
        return build_retrieval_config_model(schema_version=RETRIEVAL_CONFIG_SCHEMA_VERSION)
    return normalize_retrieval_config_model(value)


def _normalize_thresholds(value: object) -> dict[str, float]:
    data = map_value(value)
    rows: dict[str, float] = {}
    for key, default in _THRESHOLD_DEFAULTS.items():
        rows[key] = _unit_float(data.get(key), default=default)
    return rows


def _normalize_case_rows(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    rows: list[dict[str, object]] = []
    for item in value:
        rows.append(normalize_eval_case_model(item))
    rows.sort(key=lambda entry: (str(entry.get("case_id") or ""), str(entry.get("query") or "")))
    return rows


def _build_case_id(
    *,
    query: str,
    expected: dict[str, object],
    retrieval_config: dict[str, object],
) -> str:
    payload = {
        "expected": expected,
        "query": query,
        "retrieval_config": retrieval_config,
    }
    digest = canonical_contract_hash(payload)
    return f"evalcase_{digest[:20]}"


def _build_suite_id(*, name: str, cases: list[dict[str, object]]) -> str:
    payload = {
        "case_ids": [text_value(entry.get("case_id")) for entry in cases],
        "name": name,
    }
    digest = canonical_contract_hash(payload)
    return f"evalsuite_{digest[:20]}"


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

_CASE_FIELDS = {
    "schema_version",
    "case_id",
    "query",
    "expected",
    "retrieval_config",
    "thresholds",
    "tags",
    "extensions",
}

_SUITE_FIELDS = {
    "schema_version",
    "suite_id",
    "name",
    "cases",
    "extensions",
}


__all__ = [
    "EVAL_CASE_SCHEMA_VERSION",
    "EVAL_SUITE_SCHEMA_VERSION",
    "build_eval_case_model",
    "build_golden_query_suite",
    "normalize_eval_case_model",
    "normalize_golden_query_suite",
]
