from __future__ import annotations

from typing import Iterable


_OUTCOMES = ("ok", "blocked", "failed")
_FAILURE_CATEGORIES = ("input", "policy", "dependency", "internal")


def build_observability_summary(*, logs: Iterable[dict] | None, metrics: dict | None) -> dict:
    health = {outcome: 0 for outcome in _OUTCOMES}
    failure_counts: dict[str, int] = {}
    retry_counts: dict[str, int] = {}
    for entry in logs or []:
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
    quality = _quality_summary(metrics or {})
    return {
        "health": {
            "total": total,
            "ok": health["ok"],
            "blocked": health["blocked"],
            "failed": health["failed"],
        },
        "quality": quality,
        "failures": failures,
        "retries": {
            "count": sum(retry_counts.values()),
            "reasons": retries,
        },
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


def _as_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


__all__ = ["build_observability_summary"]
