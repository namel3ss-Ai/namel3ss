from __future__ import annotations

from typing import Any

from namel3ss.evals.model import EvalThresholds


def evaluate_thresholds(summary: dict[str, Any], thresholds: EvalThresholds) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    checks.extend(_check_rate("success_rate", summary.get("success_rate"), thresholds.success_rate))
    checks.extend(_check_rate("tool_accuracy", summary.get("tool_accuracy"), thresholds.tool_accuracy))
    checks.extend(_check_max("max_policy_violations", summary.get("policy_violations"), thresholds.max_policy_violations))
    return checks


def _check_rate(name: str, actual: object, minimum: float | None) -> list[dict[str, Any]]:
    if minimum is None:
        return []
    if actual is None:
        return []
    value = float(actual or 0.0)
    status = "pass" if value >= minimum else "fail"
    return [
        {
            "name": name,
            "status": status,
            "expected": minimum,
            "actual": value,
            "op": ">=",
        }
    ]


def _check_max(name: str, actual: object, maximum: int | None) -> list[dict[str, Any]]:
    if maximum is None:
        return []
    value = int(actual or 0)
    status = "pass" if value <= maximum else "fail"
    return [
        {
            "name": name,
            "status": status,
            "expected": maximum,
            "actual": value,
            "op": "<=",
        }
    ]


__all__ = ["evaluate_thresholds"]
