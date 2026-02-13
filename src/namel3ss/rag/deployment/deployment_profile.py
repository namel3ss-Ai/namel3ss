from __future__ import annotations

from namel3ss.rag.contracts.value_norms import (
    float_value,
    int_value,
    map_value,
    merge_extensions,
    sorted_string_list,
    text_value,
    unknown_extensions,
)
from namel3ss.rag.determinism.json_policy import canonical_contract_copy


SERVICE_SLO_SCHEMA_VERSION = "rag.service_slo@1"
DEPLOYMENT_PROFILE_SCHEMA_VERSION = "rag.deployment_profile@1"
LOAD_SOAK_RESULT_SCHEMA_VERSION = "rag.load_soak_result@1"
LOAD_SOAK_ASSESSMENT_SCHEMA_VERSION = "rag.load_soak_assessment@1"


def build_service_slo_model(
    *,
    availability_target: object = 0.995,
    max_error_rate: object = 0.01,
    p95_latency_ms: object = 1200,
    p99_latency_ms: object = 2500,
    max_retrieval_drift: object = 0.0,
    min_citation_grounding: object = 0.99,
    schema_version: str = SERVICE_SLO_SCHEMA_VERSION,
    extensions: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "schema_version": text_value(schema_version, default=SERVICE_SLO_SCHEMA_VERSION) or SERVICE_SLO_SCHEMA_VERSION,
        "availability_target": _ratio_float(availability_target, default=0.995),
        "max_error_rate": _ratio_float(max_error_rate, default=0.01),
        "p95_latency_ms": _positive_int(p95_latency_ms, default=1200),
        "p99_latency_ms": _positive_int(p99_latency_ms, default=2500),
        "max_retrieval_drift": _ratio_float(max_retrieval_drift, default=0.0),
        "min_citation_grounding": _ratio_float(min_citation_grounding, default=0.99),
        "extensions": merge_extensions(extensions),
    }


def normalize_service_slo_model(value: object) -> dict[str, object]:
    data = map_value(value)
    extensions = merge_extensions(
        map_value(data.get("extensions")),
        unknown_extensions(data, known_keys=_SLO_FIELDS),
    )
    return build_service_slo_model(
        availability_target=data.get("availability_target"),
        max_error_rate=data.get("max_error_rate"),
        p95_latency_ms=data.get("p95_latency_ms"),
        p99_latency_ms=data.get("p99_latency_ms"),
        max_retrieval_drift=data.get("max_retrieval_drift"),
        min_citation_grounding=data.get("min_citation_grounding"),
        schema_version=text_value(data.get("schema_version"), default=SERVICE_SLO_SCHEMA_VERSION) or SERVICE_SLO_SCHEMA_VERSION,
        extensions=extensions,
    )


def build_deployment_profile(
    *,
    environment: str = "production",
    region: str = "global",
    replicas: object = 2,
    rollout_policy: object = None,
    index_backend: str = "local",
    state_backend: str = "memory",
    stream_transport: str = "sse",
    feature_flags: object = None,
    load_targets: object = None,
    service_slo: object = None,
    schema_version: str = DEPLOYMENT_PROFILE_SCHEMA_VERSION,
    extensions: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "schema_version": text_value(schema_version, default=DEPLOYMENT_PROFILE_SCHEMA_VERSION)
        or DEPLOYMENT_PROFILE_SCHEMA_VERSION,
        "environment": _environment_value(environment),
        "region": text_value(region),
        "replicas": _positive_int(replicas, default=2),
        "rollout_policy": _normalize_rollout_policy(rollout_policy),
        "index_backend": text_value(index_backend),
        "state_backend": text_value(state_backend),
        "stream_transport": _stream_transport(stream_transport),
        "feature_flags": sorted_string_list(feature_flags),
        "load_targets": _normalize_load_targets(load_targets),
        "service_slo": normalize_service_slo_model(service_slo),
        "extensions": merge_extensions(extensions),
    }


def normalize_deployment_profile(value: object) -> dict[str, object]:
    data = map_value(value)
    extensions = merge_extensions(
        map_value(data.get("extensions")),
        unknown_extensions(data, known_keys=_DEPLOYMENT_FIELDS),
    )
    return build_deployment_profile(
        environment=text_value(data.get("environment"), default="production") or "production",
        region=text_value(data.get("region"), default="global") or "global",
        replicas=data.get("replicas"),
        rollout_policy=data.get("rollout_policy"),
        index_backend=text_value(data.get("index_backend"), default="local") or "local",
        state_backend=text_value(data.get("state_backend"), default="memory") or "memory",
        stream_transport=text_value(data.get("stream_transport"), default="sse") or "sse",
        feature_flags=data.get("feature_flags"),
        load_targets=data.get("load_targets"),
        service_slo=data.get("service_slo"),
        schema_version=text_value(data.get("schema_version"), default=DEPLOYMENT_PROFILE_SCHEMA_VERSION)
        or DEPLOYMENT_PROFILE_SCHEMA_VERSION,
        extensions=extensions,
    )


def build_load_soak_result(
    *,
    run_label: str = "",
    requests_total: object = 0,
    requests_failed: object = 0,
    latency_p95_ms: object = 0.0,
    latency_p99_ms: object = 0.0,
    soak_minutes: object = 0,
    retrieval_drift: object = 0.0,
    citation_grounding: object = 0.0,
    schema_version: str = LOAD_SOAK_RESULT_SCHEMA_VERSION,
    extensions: dict[str, object] | None = None,
) -> dict[str, object]:
    requests_total_value = _non_negative_int(requests_total, default=0)
    requests_failed_value = _non_negative_int(requests_failed, default=0)
    if requests_failed_value > requests_total_value:
        requests_failed_value = requests_total_value
    succeeded = requests_total_value - requests_failed_value
    success_rate = _safe_ratio(succeeded, requests_total_value)
    return {
        "schema_version": text_value(schema_version, default=LOAD_SOAK_RESULT_SCHEMA_VERSION)
        or LOAD_SOAK_RESULT_SCHEMA_VERSION,
        "run_label": text_value(run_label),
        "requests_total": requests_total_value,
        "requests_failed": requests_failed_value,
        "success_rate": success_rate,
        "latency_p95_ms": _non_negative_float(latency_p95_ms, default=0.0),
        "latency_p99_ms": _non_negative_float(latency_p99_ms, default=0.0),
        "soak_minutes": _non_negative_int(soak_minutes, default=0),
        "retrieval_drift": _ratio_float(retrieval_drift, default=0.0),
        "citation_grounding": _ratio_float(citation_grounding, default=0.0),
        "extensions": merge_extensions(extensions),
    }


def normalize_load_soak_result(value: object) -> dict[str, object]:
    data = map_value(value)
    extensions = merge_extensions(
        map_value(data.get("extensions")),
        unknown_extensions(data, known_keys=_LOAD_SOAK_FIELDS),
    )
    return build_load_soak_result(
        run_label=text_value(data.get("run_label")),
        requests_total=data.get("requests_total"),
        requests_failed=data.get("requests_failed"),
        latency_p95_ms=data.get("latency_p95_ms"),
        latency_p99_ms=data.get("latency_p99_ms"),
        soak_minutes=data.get("soak_minutes"),
        retrieval_drift=data.get("retrieval_drift"),
        citation_grounding=data.get("citation_grounding"),
        schema_version=text_value(data.get("schema_version"), default=LOAD_SOAK_RESULT_SCHEMA_VERSION)
        or LOAD_SOAK_RESULT_SCHEMA_VERSION,
        extensions=extensions,
    )


def evaluate_load_soak_result(
    *,
    deployment_profile: object,
    load_soak_result: object,
    schema_version: str = LOAD_SOAK_ASSESSMENT_SCHEMA_VERSION,
    extensions: dict[str, object] | None = None,
) -> dict[str, object]:
    profile = normalize_deployment_profile(deployment_profile)
    result = normalize_load_soak_result(load_soak_result)
    slo = normalize_service_slo_model(profile.get("service_slo"))
    targets = _normalize_load_targets(profile.get("load_targets"))
    checks = [
        _check_gte(
            check_id="availability_target",
            actual=result.get("success_rate"),
            required=1.0 - float(slo.get("max_error_rate") or 0.0),
        ),
        _check_lte(
            check_id="latency_p95_ms",
            actual=result.get("latency_p95_ms"),
            required=slo.get("p95_latency_ms"),
        ),
        _check_lte(
            check_id="latency_p99_ms",
            actual=result.get("latency_p99_ms"),
            required=slo.get("p99_latency_ms"),
        ),
        _check_lte(
            check_id="retrieval_drift",
            actual=result.get("retrieval_drift"),
            required=slo.get("max_retrieval_drift"),
        ),
        _check_gte(
            check_id="citation_grounding",
            actual=result.get("citation_grounding"),
            required=slo.get("min_citation_grounding"),
        ),
        _check_gte(
            check_id="soak_minutes",
            actual=result.get("soak_minutes"),
            required=targets.get("min_soak_minutes"),
        ),
        _check_gte(
            check_id="requests_total",
            actual=result.get("requests_total"),
            required=targets.get("min_requests_total"),
        ),
    ]
    checks.sort(key=lambda row: str(row.get("check_id") or ""))
    passed = all(bool(row.get("passed")) for row in checks)
    return {
        "schema_version": text_value(schema_version, default=LOAD_SOAK_ASSESSMENT_SCHEMA_VERSION)
        or LOAD_SOAK_ASSESSMENT_SCHEMA_VERSION,
        "passed": passed,
        "status": "pass" if passed else "fail",
        "profile_environment": text_value(profile.get("environment")),
        "checks": checks,
        "result": canonical_contract_copy(result),
        "service_slo": canonical_contract_copy(slo),
        "extensions": merge_extensions(extensions),
    }


def normalize_load_soak_assessment(value: object) -> dict[str, object]:
    data = map_value(value)
    checks = _normalize_check_rows(data.get("checks"))
    passed = bool(data.get("passed"))
    if checks:
        passed = all(bool(row.get("passed")) for row in checks)
    return {
        "schema_version": text_value(data.get("schema_version"), default=LOAD_SOAK_ASSESSMENT_SCHEMA_VERSION)
        or LOAD_SOAK_ASSESSMENT_SCHEMA_VERSION,
        "passed": passed,
        "status": "pass" if passed else "fail",
        "profile_environment": text_value(data.get("profile_environment")),
        "checks": checks,
        "result": normalize_load_soak_result(data.get("result")),
        "service_slo": normalize_service_slo_model(data.get("service_slo")),
        "extensions": merge_extensions(data.get("extensions")),
    }


def _normalize_rollout_policy(value: object) -> dict[str, object]:
    data = map_value(value)
    strategy = text_value(data.get("strategy"), default="rolling") or "rolling"
    if strategy not in {"rolling", "blue_green", "canary"}:
        strategy = "rolling"
    return {
        "max_surge": _non_negative_int(data.get("max_surge"), default=1),
        "max_unavailable": _non_negative_int(data.get("max_unavailable"), default=0),
        "strategy": strategy,
    }


def _normalize_load_targets(value: object) -> dict[str, object]:
    data = map_value(value)
    return {
        "min_requests_total": _non_negative_int(data.get("min_requests_total"), default=100),
        "min_soak_minutes": _non_negative_int(data.get("min_soak_minutes"), default=10),
        "target_concurrency": _non_negative_int(data.get("target_concurrency"), default=10),
    }


def _normalize_check_rows(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    rows: list[dict[str, object]] = []
    for item in value:
        data = map_value(item)
        operator = text_value(data.get("operator"), default="gte") or "gte"
        if operator not in {"gte", "lte"}:
            operator = "gte"
        rows.append(
            {
                "check_id": text_value(data.get("check_id")),
                "actual": _non_negative_float(data.get("actual"), default=0.0),
                "required": _non_negative_float(data.get("required"), default=0.0),
                "operator": operator,
                "passed": bool(data.get("passed")),
            }
        )
    rows.sort(key=lambda row: str(row.get("check_id") or ""))
    return rows


def _check_gte(*, check_id: str, actual: object, required: object) -> dict[str, object]:
    actual_value = _non_negative_float(actual, default=0.0)
    required_value = _non_negative_float(required, default=0.0)
    return {
        "check_id": check_id,
        "actual": actual_value,
        "required": required_value,
        "operator": "gte",
        "passed": actual_value >= required_value,
    }


def _check_lte(*, check_id: str, actual: object, required: object) -> dict[str, object]:
    actual_value = _non_negative_float(actual, default=0.0)
    required_value = _non_negative_float(required, default=0.0)
    return {
        "check_id": check_id,
        "actual": actual_value,
        "required": required_value,
        "operator": "lte",
        "passed": actual_value <= required_value,
    }


def _environment_value(value: object) -> str:
    token = text_value(value, default="production") or "production"
    if token not in {"dev", "staging", "production"}:
        return "production"
    return token


def _stream_transport(value: object) -> str:
    token = text_value(value, default="sse") or "sse"
    if token not in {"sse", "none"}:
        return "sse"
    return token


def _safe_ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return _ratio_float(float(numerator) / float(denominator), default=0.0)


def _ratio_float(value: object, *, default: float) -> float:
    number = float_value(value, default=default, precision=6)
    if number < 0:
        return 0.0
    if number > 1:
        return 1.0
    return number


def _positive_int(value: object, *, default: int) -> int:
    return int_value(value, default=default, minimum=1)


def _non_negative_int(value: object, *, default: int) -> int:
    return int_value(value, default=default, minimum=0)


def _non_negative_float(value: object, *, default: float) -> float:
    number = float_value(value, default=default, precision=6)
    if number < 0:
        return 0.0
    return number


_SLO_FIELDS = {
    "schema_version",
    "availability_target",
    "max_error_rate",
    "p95_latency_ms",
    "p99_latency_ms",
    "max_retrieval_drift",
    "min_citation_grounding",
    "extensions",
}

_DEPLOYMENT_FIELDS = {
    "schema_version",
    "environment",
    "region",
    "replicas",
    "rollout_policy",
    "index_backend",
    "state_backend",
    "stream_transport",
    "feature_flags",
    "load_targets",
    "service_slo",
    "extensions",
}

_LOAD_SOAK_FIELDS = {
    "schema_version",
    "run_label",
    "requests_total",
    "requests_failed",
    "success_rate",
    "latency_p95_ms",
    "latency_p99_ms",
    "soak_minutes",
    "retrieval_drift",
    "citation_grounding",
    "extensions",
}


__all__ = [
    "DEPLOYMENT_PROFILE_SCHEMA_VERSION",
    "LOAD_SOAK_ASSESSMENT_SCHEMA_VERSION",
    "LOAD_SOAK_RESULT_SCHEMA_VERSION",
    "SERVICE_SLO_SCHEMA_VERSION",
    "build_deployment_profile",
    "build_load_soak_result",
    "build_service_slo_model",
    "evaluate_load_soak_result",
    "normalize_deployment_profile",
    "normalize_load_soak_assessment",
    "normalize_load_soak_result",
    "normalize_service_slo_model",
]
