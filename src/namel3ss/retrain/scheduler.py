from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from namel3ss.determinism import canonical_json_dump
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.evals.ai_flow_eval import load_ai_flow_evals
from namel3ss.feedback import load_feedback_entries, summarize_feedback
from namel3ss.observability.ai_metrics import load_ai_metrics, summarize_ai_metrics
from namel3ss.runtime.ai.models_config import load_models_config
from namel3ss.runtime.persistence_paths import resolve_persistence_root, resolve_project_root
from namel3ss.utils.simple_yaml import parse_yaml


RETRAIN_FILENAME = "retrain.json"
THRESHOLDS_FILENAME = "feedback.yaml"
RETRAIN_CONFIG_FILENAME = "retrain.yaml"
ALLOWED_THRESHOLD_KEYS = {
    "min_positive_ratio",
    "min_accuracy",
    "min_completion_quality",
    "min_f1",
    "max_drift",
    "schedule",
    "threshold_window",
    "negative_feedback_count",
}
DEFAULT_THRESHOLDS = {
    "min_positive_ratio": 0.8,
    "min_accuracy": 0.9,
    "min_completion_quality": 0.9,
    "min_f1": 0.85,
    "max_drift": 0.2,
    "schedule": "manual",
    "threshold_window": 20,
    "negative_feedback_count": 5,
}


@dataclass(frozen=True)
class RetrainSuggestion:
    model_name: str
    reason: str
    affected_flows: tuple[str, ...]
    suggested_action: str

    def to_dict(self) -> dict[str, object]:
        return {
            "model_name": self.model_name,
            "reason": self.reason,
            "affected_flows": list(self.affected_flows),
            "suggested_action": self.suggested_action,
        }



def retrain_path(project_root: str | Path | None, app_path: str | Path | None, *, allow_create: bool = True) -> Path | None:
    root = resolve_persistence_root(project_root, app_path, allow_create=allow_create)
    if root is None:
        return None
    return Path(root) / ".namel3ss" / RETRAIN_FILENAME



def load_thresholds(project_root: str | Path | None, app_path: str | Path | None) -> dict[str, object]:
    root = resolve_project_root(project_root, app_path)
    if root is None:
        return dict(DEFAULT_THRESHOLDS)
    retrain_path = Path(root) / RETRAIN_CONFIG_FILENAME
    path = retrain_path if retrain_path.exists() else (Path(root) / THRESHOLDS_FILENAME)
    if not path.exists():
        return dict(DEFAULT_THRESHOLDS)
    try:
        payload = parse_yaml(path.read_text(encoding="utf-8"))
    except Exception as err:
        raise Namel3ssError(_invalid_thresholds_message(path, str(err))) from err
    if not isinstance(payload, dict):
        raise Namel3ssError(_invalid_thresholds_message(path, "expected a YAML map"))
    unknown = sorted([key for key in payload.keys() if str(key) not in ALLOWED_THRESHOLD_KEYS])
    if unknown:
        joined = ", ".join(unknown)
        raise Namel3ssError(_invalid_thresholds_message(path, f"unknown keys: {joined}"))
    thresholds = dict(DEFAULT_THRESHOLDS)
    for key in ["min_positive_ratio", "min_accuracy", "min_completion_quality", "min_f1", "max_drift"]:
        if key not in payload:
            continue
        raw = payload.get(key)
        parsed = _parse_ratio(raw)
        if parsed is None:
            raise Namel3ssError(_invalid_thresholds_message(path, f"{key} must be a number in range 0..1"))
        thresholds[key] = parsed
    if "schedule" in payload:
        schedule = str(payload.get("schedule") or "").strip()
        if not schedule:
            raise Namel3ssError(_invalid_thresholds_message(path, "schedule must be a non-empty string"))
        thresholds["schedule"] = schedule
    for key in ["threshold_window", "negative_feedback_count"]:
        if key not in payload:
            continue
        parsed_int = _parse_non_negative_int(payload.get(key))
        if parsed_int is None:
            raise Namel3ssError(_invalid_thresholds_message(path, f"{key} must be a non-negative integer"))
        thresholds[key] = parsed_int
    return thresholds



def build_retrain_payload(project_root: str | Path | None, app_path: str | Path | None) -> dict[str, object]:
    feedback_entries = load_feedback_entries(project_root, app_path)
    feedback_summary = summarize_feedback(feedback_entries)
    metrics_summary = summarize_ai_metrics(load_ai_metrics(project_root, app_path))
    eval_summary = _summarize_eval_metrics(load_ai_flow_evals(project_root, app_path))
    thresholds = load_thresholds(project_root, app_path)

    positive_ratio = _metric_or_default(feedback_summary, "positive_ratio", 1.0)
    completion_quality = _metric_or_default(feedback_summary, "completion_quality", 1.0)
    min_accuracy_value = _metric_or_default(metrics_summary, "classification_accuracy", 1.0)
    min_f1_value = _metric_or_default(eval_summary, "f1_score", min_accuracy_value)
    drift_value = _compute_drift(min_accuracy_value, min_f1_value)
    negative_feedback = int(feedback_summary.get("bad") or 0)

    checks = {
        "min_positive_ratio": {
            "value": positive_ratio,
            "threshold": float(thresholds["min_positive_ratio"]),
            "triggered": positive_ratio < float(thresholds["min_positive_ratio"]),
        },
        "min_accuracy": {
            "value": min_accuracy_value,
            "threshold": float(thresholds["min_accuracy"]),
            "triggered": min_accuracy_value < float(thresholds["min_accuracy"]),
        },
        "min_completion_quality": {
            "value": completion_quality,
            "threshold": float(thresholds["min_completion_quality"]),
            "triggered": completion_quality < float(thresholds["min_completion_quality"]),
        },
        "min_f1": {
            "value": min_f1_value,
            "threshold": float(thresholds["min_f1"]),
            "triggered": min_f1_value < float(thresholds["min_f1"]),
        },
        "max_drift": {
            "value": drift_value,
            "threshold": float(thresholds["max_drift"]),
            "triggered": drift_value > float(thresholds["max_drift"]),
        },
        "negative_feedback_count": {
            "value": negative_feedback,
            "threshold": int(thresholds["negative_feedback_count"]),
            "triggered": negative_feedback >= int(thresholds["negative_feedback_count"]),
        },
    }

    suggestions = _build_suggestions(project_root, app_path, feedback_entries, checks)
    return {
        "ok": True,
        "schema_version": 1,
        "metrics": {
            "feedback": feedback_summary,
            "ai": metrics_summary,
            "eval": eval_summary,
        },
        "thresholds": checks,
        "config": {
            "schedule": thresholds["schedule"],
            "threshold_window": int(thresholds["threshold_window"]),
            "negative_feedback_count": int(thresholds["negative_feedback_count"]),
        },
        "suggestions": [item.to_dict() for item in suggestions],
    }



def write_retrain_payload(project_root: str | Path | None, app_path: str | Path | None) -> Path:
    payload = build_retrain_payload(project_root, app_path)
    path = retrain_path(project_root, app_path)
    if path is None:
        raise Namel3ssError(
            build_guidance_message(
                what="Retrain path could not be resolved.",
                why="The project root is missing.",
                fix="Run this command from a project with app.ai.",
                example="n3 retrain schedule",
            )
        )
    canonical_json_dump(path, payload, pretty=True, drop_run_keys=False)
    return path



def _build_suggestions(
    project_root: str | Path | None,
    app_path: str | Path | None,
    feedback_entries,
    checks: dict[str, dict[str, object]],
) -> list[RetrainSuggestion]:
    triggered = [name for name in sorted(checks.keys()) if bool(checks[name].get("triggered"))]
    if not triggered:
        return []

    models_config = load_models_config(project_root, app_path)
    model_names = sorted(models_config.models.keys())
    if not model_names:
        model_names = ["default"]

    affected_flows = sorted({entry.flow_name for entry in feedback_entries if entry.flow_name})
    if not affected_flows:
        affected_flows = ["default"]

    reason_parts: list[str] = []
    for key in triggered:
        entry = checks[key]
        value = _format_ratio(entry.get("value"))
        threshold = _format_ratio(entry.get("threshold"))
        if key == "max_drift":
            reason_parts.append(f"{key} {value} > {threshold}")
            continue
        if key == "negative_feedback_count":
            reason_parts.append(f"{key} {value} >= {threshold}")
            continue
        reason_parts.append(f"{key} {value} < {threshold}")
    reason = "; ".join(reason_parts)

    suggestions: list[RetrainSuggestion] = []
    for model_name in model_names:
        suggestions.append(
            RetrainSuggestion(
                model_name=model_name,
                reason=reason,
                affected_flows=tuple(affected_flows),
                suggested_action="Collect more labeled examples, run offline eval, then publish a new model version.",
            )
        )
    return suggestions



def _parse_ratio(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        parsed = float(value)
    except Exception:
        return None
    if parsed < 0.0 or parsed > 1.0:
        return None
    return parsed



def _parse_non_negative_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        parsed = int(value)
    except Exception:
        return None
    if parsed < 0:
        return None
    return parsed



def _metric_or_default(summary: dict[str, object], key: str, default: float) -> float:
    value = summary.get(key)
    if value is None:
        return default
    try:
        return float(value)
    except Exception:
        return default


def _summarize_eval_metrics(evals: list[dict]) -> dict[str, object]:
    values: list[float] = []
    for item in evals:
        if not isinstance(item, dict):
            continue
        results = item.get("results")
        if not isinstance(results, dict):
            continue
        if "f1_score" in results:
            try:
                values.append(float(results["f1_score"]))
            except Exception:
                continue
            continue
        if "f1" in results:
            try:
                values.append(float(results["f1"]))
            except Exception:
                continue
    if not values:
        return {}
    return {"f1_score": sum(values) / len(values)}


def _compute_drift(accuracy: float, f1_score: float) -> float:
    accuracy_gap = max(0.0, 1.0 - float(accuracy))
    f1_gap = max(0.0, 1.0 - float(f1_score))
    return max(accuracy_gap, f1_gap)


def _format_ratio(value: object) -> str:
    try:
        return f"{float(value):.3f}"
    except Exception:
        return "0.000"



def _invalid_thresholds_message(path: Path, details: str) -> str:
    filename = path.name
    return build_guidance_message(
        what=f"{filename} is invalid.",
        why=f"{path.as_posix()} could not be parsed: {details}.",
        fix=(
            "Use min_positive_ratio, min_accuracy, min_completion_quality, min_f1, and max_drift in range 0..1, "
            "plus optional schedule, threshold_window, and negative_feedback_count."
        ),
        example=(
            "min_positive_ratio: 0.8\n"
            "min_accuracy: 0.9\n"
            "min_completion_quality: 0.9\n"
            "min_f1: 0.85\n"
            "max_drift: 0.2"
        ),
    )


__all__ = [
    "ALLOWED_THRESHOLD_KEYS",
    "DEFAULT_THRESHOLDS",
    "RETRAIN_CONFIG_FILENAME",
    "RETRAIN_FILENAME",
    "RetrainSuggestion",
    "build_retrain_payload",
    "load_thresholds",
    "retrain_path",
    "write_retrain_payload",
]
