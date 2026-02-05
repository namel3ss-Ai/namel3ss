from __future__ import annotations

import hashlib
import json
from pathlib import Path

from namel3ss.determinism import canonical_json_dump, canonical_json_dumps
from namel3ss.runtime.persistence_paths import resolve_persistence_root


METRICS_DIRNAME = "metrics"
AI_METRICS_FILENAME = "ai_metrics.json"
THRESHOLDS_FILENAME = "thresholds.json"


def ai_metrics_path(
    project_root: str | Path | None,
    app_path: str | Path | None,
    *,
    allow_create: bool = True,
) -> Path | None:
    root = resolve_persistence_root(project_root, app_path, allow_create=allow_create)
    if root is None:
        return None
    return Path(root) / ".namel3ss" / "observability" / METRICS_DIRNAME / AI_METRICS_FILENAME


def thresholds_path(
    project_root: str | Path | None,
    app_path: str | Path | None,
    *,
    allow_create: bool = True,
) -> Path | None:
    root = resolve_persistence_root(project_root, app_path, allow_create=allow_create)
    if root is None:
        return None
    return Path(root) / ".namel3ss" / "observability" / METRICS_DIRNAME / THRESHOLDS_FILENAME


def load_ai_metrics(project_root: str | Path | None, app_path: str | Path | None) -> list[dict]:
    path = ai_metrics_path(project_root, app_path, allow_create=False)
    if path is None or not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    records = payload.get("records") if isinstance(payload, dict) else None
    return records if isinstance(records, list) else []


def record_ai_metric(
    *,
    project_root: str | Path | None,
    app_path: str | Path | None,
    record: dict,
) -> None:
    path = ai_metrics_path(project_root, app_path)
    if path is None:
        return
    existing = load_ai_metrics(project_root, app_path)
    cleaned = _clean_record(record)
    existing.append(cleaned)
    sorted_records = sorted(existing, key=_record_sort_key)
    payload = {"schema_version": 1, "records": sorted_records}
    canonical_json_dump(path, payload, pretty=True)


def build_ai_record(
    *,
    flow_name: str,
    kind: str,
    input_text: str,
    output_text: str,
    expected: str | None,
    accuracy: float | None,
    latency_steps: int,
    prompt_tokens: int | None,
    completion_tokens: int | None,
) -> dict:
    record = {
        "flow_name": flow_name,
        "type": kind,
        "input_id": _input_id(input_text),
        "output": output_text,
        "latency_steps": int(latency_steps),
    }
    if expected is not None:
        record["expected"] = expected
    if accuracy is not None:
        record["accuracy"] = float(accuracy)
    if prompt_tokens is not None:
        record["prompt_tokens"] = int(prompt_tokens)
    if completion_tokens is not None:
        record["completion_tokens"] = int(completion_tokens)
    return record


def summarize_ai_metrics(records: list[dict]) -> dict:
    accuracy_values = []
    latency_values = []
    prompt_tokens_values = []
    completion_tokens_values = []
    for record in records:
        if isinstance(record, dict):
            if record.get("accuracy") is not None:
                accuracy_values.append(float(record.get("accuracy") or 0.0))
            if record.get("latency_steps") is not None:
                latency_values.append(int(record.get("latency_steps") or 0))
            if record.get("prompt_tokens") is not None:
                prompt_tokens_values.append(int(record.get("prompt_tokens") or 0))
            if record.get("completion_tokens") is not None:
                completion_tokens_values.append(int(record.get("completion_tokens") or 0))
    summary: dict[str, object] = {"total_calls": len(records)}
    if accuracy_values:
        summary["classification_accuracy"] = sum(accuracy_values) / len(accuracy_values)
    if latency_values:
        summary["latency_steps_avg"] = sum(latency_values) / len(latency_values)
    if prompt_tokens_values:
        summary["prompt_tokens_avg"] = sum(prompt_tokens_values) / len(prompt_tokens_values)
    if completion_tokens_values:
        summary["completion_tokens_avg"] = sum(completion_tokens_values) / len(completion_tokens_values)
    return summary


def load_thresholds(project_root: str | Path | None, app_path: str | Path | None) -> dict[str, float]:
    path = thresholds_path(project_root, app_path, allow_create=False)
    if path is None or not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(payload, dict):
        return {}
    thresholds: dict[str, float] = {}
    for key, value in payload.items():
        try:
            thresholds[str(key)] = float(value)
        except Exception:
            continue
    return thresholds


def apply_thresholds(summary: dict, thresholds: dict[str, float]) -> list[dict]:
    results = []
    for name in sorted(thresholds.keys()):
        threshold = thresholds[name]
        value = summary.get(name)
        if value is None:
            results.append({"metric": name, "value": None, "threshold": threshold, "drifted": False})
            continue
        drifted = float(value) < float(threshold)
        results.append({"metric": name, "value": value, "threshold": threshold, "drifted": drifted})
    return results


def _clean_record(record: dict) -> dict:
    cleaned = {k: v for k, v in record.items() if v is not None}
    return cleaned


def _record_sort_key(record: dict) -> tuple:
    return (
        str(record.get("flow_name") or ""),
        str(record.get("input_id") or ""),
        str(record.get("output") or ""),
    )


def _input_id(input_text: str) -> str:
    payload = canonical_json_dumps(input_text, pretty=False, drop_run_keys=False)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return digest[:12]


__all__ = [
    "ai_metrics_path",
    "thresholds_path",
    "load_ai_metrics",
    "record_ai_metric",
    "build_ai_record",
    "summarize_ai_metrics",
    "load_thresholds",
    "apply_thresholds",
]
