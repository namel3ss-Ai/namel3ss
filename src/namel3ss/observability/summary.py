from __future__ import annotations

from typing import Iterable


_OUTCOMES = ("ok", "blocked", "failed")
_FAILURE_CATEGORIES = ("input", "policy", "dependency", "internal")
_MAX_EXECUTIONS = 5


def build_observability_summary(*, logs: Iterable[dict] | None, metrics: dict | None) -> dict:
    health = {outcome: 0 for outcome in _OUTCOMES}
    failure_counts: dict[str, int] = {}
    retry_counts: dict[str, int] = {}
    log_entries = list(logs or [])
    for entry in log_entries:
        if not isinstance(entry, dict):
            continue
        event_kind = _as_text(entry.get("event_kind"))
        outcome = _as_text(entry.get("outcome"))
        if event_kind == "run" and outcome in health:
            health[outcome] += 1
        if event_kind == "retry":
            reason = _as_text(_payload_value(entry, "reason")) or "unspecified"
            retry_counts[reason] = retry_counts.get(reason, 0) + 1
        if outcome == "failed":
            category = _normalize_category(_payload_value(entry, "error_category"))
            failure_counts[category] = failure_counts.get(category, 0) + 1
    total = sum(health.values())
    failures = [{"category": cat, "count": failure_counts.get(cat, 0)} for cat in sorted(failure_counts.keys())]
    retries = [{"reason": reason, "count": retry_counts[reason]} for reason in sorted(retry_counts.keys())]
    metrics_payload = metrics or {}
    quality = _quality_summary(metrics_payload)
    executions = _execution_summary(log_entries)
    retrieval = _retrieval_summary(log_entries)
    cost = _cost_summary(metrics_payload)
    return {
        "health": {
            "total": total,
            "ok": health["ok"],
            "blocked": health["blocked"],
            "failed": health["failed"],
        },
        "executions": executions,
        "retrieval": retrieval,
        "quality": quality,
        "failures": failures,
        "retries": {
            "count": sum(retry_counts.values()),
            "reasons": retries,
        },
        "cost": cost,
    }


def _quality_summary(metrics: dict) -> dict:
    coverage = _metric_value(metrics, names=("quality.coverage", "coverage"), scope="quality")
    faithfulness = _metric_value(metrics, names=("quality.faithfulness", "faithfulness"), scope="quality")
    available = coverage is not None or faithfulness is not None
    return {
        "status": "available" if available else "not_available",
        "coverage": coverage,
        "faithfulness": faithfulness,
    }


def _execution_summary(logs: list[dict]) -> dict:
    runs: list[dict] = []
    for entry in logs:
        if not isinstance(entry, dict):
            continue
        if _as_text(entry.get("event_kind")) != "run":
            continue
        runs.append(
            {
                "id": _as_text(entry.get("id")),
                "scope": _as_text(entry.get("scope")),
                "outcome": _as_text(entry.get("outcome")),
                "order": _event_order(entry),
            }
        )
    runs.sort(key=lambda item: item.get("order", 0))
    recent = runs[-_MAX_EXECUTIONS:] if runs else []
    entries = [
        {"id": entry.get("id"), "scope": entry.get("scope"), "outcome": entry.get("outcome")}
        for entry in recent
    ]
    return {"status": "available" if entries else "not_available", "entries": entries}


def _retrieval_summary(logs: list[dict]) -> dict:
    latest: dict | None = None
    latest_order = -1
    for entry in logs:
        if not isinstance(entry, dict):
            continue
        if _as_text(entry.get("event_kind")) != "run":
            continue
        if _as_text(entry.get("scope")) != "retrieval":
            continue
        order = _event_order(entry)
        if order >= latest_order:
            latest_order = order
            latest = entry
    if latest is None:
        return {"status": "not_available"}
    return {
        "status": "available",
        "result_count": _int_value(_payload_value(latest, "result_count")),
        "preferred_quality": _as_text(_payload_value(latest, "preferred_quality")),
        "included_warn": _bool_value(_payload_value(latest, "included_warn")),
        "excluded_warn": _int_value(_payload_value(latest, "excluded_warn")),
        "excluded_blocked": _int_value(_payload_value(latest, "excluded_blocked")),
        "warn_allowed": _bool_value(_payload_value(latest, "warn_allowed")),
    }


def _cost_summary(metrics: dict) -> dict:
    counters = metrics.get("counters")
    if not isinstance(counters, list):
        return {"status": "not_available", "entries": []}
    entries: list[dict] = []
    for entry in counters:
        if not isinstance(entry, dict):
            continue
        name = _as_text(entry.get("name"))
        labels = entry.get("labels")
        label_map = labels if isinstance(labels, dict) else {}
        if not name:
            continue
        if name.startswith("cost.") or label_map.get("scope") == "cost":
            entries.append(
                {
                    "name": name,
                    "value": _coerce_number(entry.get("value")),
                    "labels": label_map,
                }
            )
    entries.sort(key=_metric_sort_key)
    return {"status": "available" if entries else "not_available", "entries": entries}


def _metric_value(metrics: dict, *, names: tuple[str, ...], scope: str | None) -> float | None:
    counters = metrics.get("counters")
    if not isinstance(counters, list):
        return None
    for entry in counters:
        if not isinstance(entry, dict):
            continue
        name = _as_text(entry.get("name"))
        if name not in names:
            continue
        labels = entry.get("labels")
        if scope and not _labels_match(labels, {"scope": scope}):
            continue
        value = entry.get("value")
        try:
            return float(value)
        except Exception:
            return None
    return None


def _metric_sort_key(entry: dict) -> tuple:
    name = _as_text(entry.get("name"))
    labels = entry.get("labels", {})
    label_key = tuple((str(key), str(labels.get(key))) for key in sorted(labels.keys(), key=lambda item: str(item)))
    return (name, label_key)


def _labels_match(labels: object, expected: dict) -> bool:
    if not isinstance(labels, dict):
        return False
    for key, value in expected.items():
        if labels.get(key) != value:
            return False
    return True


def _payload_value(entry: dict, key: str) -> object:
    payload = entry.get("payload")
    if not isinstance(payload, dict):
        return None
    return payload.get(key)


def _normalize_category(value: object) -> str:
    text = _as_text(value)
    if text in _FAILURE_CATEGORIES:
        return text
    return "internal"


def _event_order(entry: dict) -> int:
    value = entry.get("order")
    if isinstance(value, int):
        return value
    try:
        return int(value)  # type: ignore[arg-type]
    except Exception:
        return 0


def _int_value(value: object) -> int:
    if isinstance(value, bool):
        return 1 if value else 0
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    try:
        return int(value)  # type: ignore[arg-type]
    except Exception:
        return 0


def _bool_value(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes"}
    return bool(value)


def _coerce_number(value: object) -> float:
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(value)  # type: ignore[arg-type]
    except Exception:
        return 0.0


def _as_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


__all__ = ["build_observability_summary"]
