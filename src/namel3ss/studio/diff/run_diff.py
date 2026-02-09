from __future__ import annotations

from collections.abc import Mapping

from namel3ss.runtime.audit.run_artifact import compute_component_hash


RUN_DIFF_SCHEMA_VERSION = "studio_run_diff@1"
RUN_DIFF_FIELD_ORDER: tuple[str, ...] = (
    "inputs",
    "retrieval_trace",
    "prompt",
    "output",
    "trust_score_details",
)


def build_run_diff(
    left_artifact: Mapping[str, object] | None,
    right_artifact: Mapping[str, object] | None,
) -> dict[str, object]:
    left = _mapping_or_empty(left_artifact)
    right = _mapping_or_empty(right_artifact)
    changes = []
    change_count = 0
    for field in RUN_DIFF_FIELD_ORDER:
        left_value = _field_value(left, field)
        right_value = _field_value(right, field)
        left_hash = compute_component_hash(left_value)
        right_hash = compute_component_hash(right_value)
        changed = left_hash != right_hash
        if changed:
            change_count += 1
        changes.append(
            {
                "field": field,
                "changed": changed,
                "left_hash": left_hash,
                "right_hash": right_hash,
            }
        )
    return {
        "schema_version": RUN_DIFF_SCHEMA_VERSION,
        "left_run_id": _text(left.get("run_id")),
        "right_run_id": _text(right.get("run_id")),
        "changed": change_count > 0,
        "change_count": change_count,
        "changes": changes,
    }


def _field_value(artifact: Mapping[str, object], field: str) -> object:
    if field == "inputs":
        return artifact.get("inputs")
    if field == "retrieval_trace":
        return artifact.get("retrieval_trace")
    if field == "prompt":
        return artifact.get("prompt")
    if field == "output":
        return artifact.get("output")
    if field == "trust_score_details":
        return artifact.get("trust_score_details")
    return None


def _mapping_or_empty(value: Mapping[str, object] | None) -> dict[str, object]:
    if not isinstance(value, Mapping):
        return {}
    return {str(key): value[key] for key in value.keys()}


def _text(value: object) -> str:
    if isinstance(value, str):
        return value.strip()
    return ""


__all__ = ["RUN_DIFF_FIELD_ORDER", "RUN_DIFF_SCHEMA_VERSION", "build_run_diff"]
