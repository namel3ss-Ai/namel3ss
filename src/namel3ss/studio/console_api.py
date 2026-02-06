from __future__ import annotations

import json
from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.feedback import load_feedback_entries, summarize_feedback
from namel3ss.lint.engine import lint_source
from namel3ss.marketplace import search_items
from namel3ss.mlops import load_mlops_config, mlops_snapshot_path
from namel3ss.module_loader import load_project
from namel3ss.observability.ai_metrics import load_ai_metrics, summarize_ai_metrics
from namel3ss.quality import run_quality_checks
from namel3ss.retrain import ALLOWED_THRESHOLD_KEYS, build_retrain_payload
from namel3ss.runtime.ai.models_config import load_models_config, models_path
from namel3ss.runtime.ai.canary_results import load_canary_results, summarize_canary_results
from namel3ss.runtime.persistence_paths import resolve_project_root
from namel3ss.utils.simple_yaml import parse_yaml, render_yaml
from namel3ss.versioning import list_versions, load_version_config



def get_console_payload(source: str, app_path: str) -> dict[str, object]:
    app_file = Path(app_path)
    project = load_project(app_file, source_overrides={app_file: source})
    program = project.program

    lint_findings = lint_source(source)
    models = load_models_config(app_file.parent, app_file)
    metrics_summary = summarize_ai_metrics(load_ai_metrics(app_file.parent, app_file))
    feedback_entries = load_feedback_entries(app_file.parent, app_file)
    feedback_summary = summarize_feedback(feedback_entries)
    retrain_preview = build_retrain_payload(app_file.parent, app_file)
    canary_summary = summarize_canary_results(load_canary_results(app_file.parent, app_file))
    version_config = load_version_config(app_file.parent, app_file)
    version_rows = list_versions(version_config)
    quality_report = run_quality_checks(source, project_root=app_file.parent, app_path=app_file)
    mlops_config = load_mlops_config(app_file.parent, app_file, required=False)
    mlops_models = _read_mlops_models(app_file.parent, app_file)

    return {
        "ok": True,
        "source": source,
        "lint": {
            "ok": len(lint_findings) == 0,
            "count": len(lint_findings),
            "findings": [finding.to_dict() for finding in lint_findings],
        },
        "definitions": {
            "routes": [
                {
                    "name": route.name,
                    "path": route.path,
                    "method": route.method,
                    "flow": route.flow_name,
                }
                for route in sorted(program.routes, key=lambda item: (item.name, item.path, item.method))
            ],
            "flows": [flow.name for flow in sorted(program.flows, key=lambda item: item.name)],
            "prompts": [prompt.name for prompt in sorted(program.prompts, key=lambda item: item.name)],
            "datasets": [record.name for record in sorted(program.records, key=lambda item: item.name)],
            "ai_flows": [flow.name for flow in sorted(program.ai_flows, key=lambda item: item.name)],
        },
        "metadata": {
            "models": [
                {
                    "name": spec.name,
                    "version": spec.version,
                    "image": spec.image,
                    "canary_fraction": spec.canary_fraction,
                    "canary_target": spec.canary_target,
                    "shadow_target": spec.shadow_target,
                }
                for spec in [models.models[name] for name in sorted(models.models.keys())]
            ],
            "dataset_lineage": _dataset_lineage(app_file.parent),
            "health": {
                "ai_metrics": metrics_summary,
                "feedback": feedback_summary,
                "retrain_suggestions": retrain_preview.get("suggestions", []),
                "canary": canary_summary,
                "quality": {
                    "ok": quality_report.get("ok"),
                    "count": quality_report.get("count"),
                },
            },
            "versioning": {
                "count": len(version_rows),
                "deprecated_count": len([item for item in version_rows if item.get("status") == "deprecated"]),
                "removed_count": len([item for item in version_rows if item.get("status") == "removed"]),
            },
            "mlops": {
                "configured": mlops_config is not None,
                "models": mlops_models,
                "count": len(mlops_models),
            },
            "marketplace_preview": search_items(
                project_root=app_file.parent,
                app_path=app_file,
                query="",
                include_pending=False,
            )[:10],
        },
        "files": {
            "models_yaml": _read_models_yaml(app_file.parent, app_file),
            "feedback_yaml": _read_feedback_yaml(app_file.parent, app_file),
            "versions_yaml": _read_project_yaml(app_file.parent, app_file, "versions.yaml"),
            "quality_yaml": _read_project_yaml(app_file.parent, app_file, "quality.yaml"),
            "mlops_yaml": _read_project_yaml(app_file.parent, app_file, "mlops.yaml"),
        },
    }



def validate_console_payload(source: str, body: dict, app_path: str) -> dict[str, object]:
    candidate = body.get("source") if isinstance(body.get("source"), str) else source
    app_file = Path(app_path)
    _require_parseable(candidate, app_file)
    findings = lint_source(candidate)
    return {
        "ok": len(findings) == 0,
        "count": len(findings),
        "findings": [item.to_dict() for item in findings],
    }



def save_console_payload(source: str, body: dict, app_path: str) -> dict[str, object]:
    app_file = Path(app_path)
    candidate_source = body.get("source") if isinstance(body.get("source"), str) else source
    _require_parseable(candidate_source, app_file)
    findings = lint_source(candidate_source)
    if findings:
        return {
            "ok": False,
            "error": "Fix lint findings before saving.",
            "count": len(findings),
            "findings": [item.to_dict() for item in findings],
        }

    saved: list[str] = []
    app_file.write_text(_normalize_newlines(candidate_source), encoding="utf-8")
    saved.append(app_file.as_posix())

    models_yaml = body.get("models_yaml")
    if isinstance(models_yaml, str):
        models_payload = parse_yaml(models_yaml)
        if not isinstance(models_payload, dict):
            raise Namel3ssError(_invalid_console_file_message("models.yaml", "expected YAML mapping"))
        model_path = models_path(app_file.parent, app_file)
        if model_path is None:
            raise Namel3ssError(_invalid_console_file_message("models.yaml", "path could not be resolved"))
        model_path.parent.mkdir(parents=True, exist_ok=True)
        model_path.write_text(render_yaml(models_payload), encoding="utf-8")
        saved.append(model_path.as_posix())

    feedback_yaml = body.get("feedback_yaml")
    if isinstance(feedback_yaml, str):
        feedback_payload = parse_yaml(feedback_yaml)
        if not isinstance(feedback_payload, dict):
            raise Namel3ssError(_invalid_console_file_message("feedback.yaml", "expected YAML mapping"))
        unknown = sorted([key for key in feedback_payload.keys() if str(key) not in ALLOWED_THRESHOLD_KEYS])
        if unknown:
            joined = ", ".join(unknown)
            raise Namel3ssError(_invalid_console_file_message("feedback.yaml", f"unknown keys: {joined}"))
        for key in sorted(ALLOWED_THRESHOLD_KEYS):
            if key not in feedback_payload:
                continue
            value = feedback_payload.get(key)
            if key in {"min_positive_ratio", "min_accuracy", "min_completion_quality", "min_f1", "max_drift"}:
                if isinstance(value, bool):
                    raise Namel3ssError(_invalid_console_file_message("feedback.yaml", f"{key} must be 0..1"))
                try:
                    parsed = float(value)
                except Exception:
                    raise Namel3ssError(_invalid_console_file_message("feedback.yaml", f"{key} must be 0..1"))
                if parsed < 0.0 or parsed > 1.0:
                    raise Namel3ssError(_invalid_console_file_message("feedback.yaml", f"{key} must be 0..1"))
                continue
            if key in {"threshold_window", "negative_feedback_count"}:
                if isinstance(value, bool):
                    raise Namel3ssError(_invalid_console_file_message("feedback.yaml", f"{key} must be a non-negative integer"))
                try:
                    parsed_int = int(value)
                except Exception:
                    raise Namel3ssError(_invalid_console_file_message("feedback.yaml", f"{key} must be a non-negative integer"))
                if parsed_int < 0:
                    raise Namel3ssError(_invalid_console_file_message("feedback.yaml", f"{key} must be a non-negative integer"))
                continue
            if key == "schedule":
                text = str(value or "").strip()
                if not text:
                    raise Namel3ssError(_invalid_console_file_message("feedback.yaml", "schedule must be a non-empty string"))
                continue
        feedback_path = app_file.parent / "feedback.yaml"
        feedback_path.write_text(render_yaml(feedback_payload), encoding="utf-8")
        saved.append(feedback_path.as_posix())

    return {
        "ok": True,
        "saved": saved,
        "lint": {"ok": True, "count": 0, "findings": []},
    }



def _require_parseable(source: str, app_file: Path) -> None:
    try:
        load_project(app_file, source_overrides={app_file: source})
    except Exception as err:
        raise Namel3ssError(
            build_guidance_message(
                what="Console source could not be parsed.",
                why=str(err),
                fix="Fix parser errors and retry.",
                example="n3 check app.ai",
            )
        ) from err



def _read_models_yaml(project_root: Path, app_file: Path) -> str:
    path = models_path(project_root, app_file)
    if path is None or not path.exists():
        return "models: {}\n"
    return path.read_text(encoding="utf-8")



def _read_feedback_yaml(project_root: Path, app_file: Path) -> str:
    root = resolve_project_root(project_root, app_file)
    if root is None:
        return "min_positive_ratio: 0.8\nmin_accuracy: 0.9\nmin_completion_quality: 0.9\n"
    path = Path(root) / "feedback.yaml"
    if not path.exists():
        return "min_positive_ratio: 0.8\nmin_accuracy: 0.9\nmin_completion_quality: 0.9\n"
    return path.read_text(encoding="utf-8")


def _read_project_yaml(project_root: Path, app_file: Path, filename: str) -> str:
    root = resolve_project_root(project_root, app_file)
    if root is None:
        return ""
    path = Path(root) / filename
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _read_mlops_models(project_root: Path, app_file: Path) -> list[dict[str, object]]:
    path = mlops_snapshot_path(project_root, app_file)
    if path is None or not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    if not isinstance(payload, dict):
        return []
    values = payload.get("models")
    if not isinstance(values, list):
        return []
    return [item for item in values if isinstance(item, dict)]



def _dataset_lineage(project_root: Path) -> list[dict[str, object]]:
    lineage_path = project_root / ".namel3ss" / "ingestion" / "lineage.json"
    if not lineage_path.exists():
        return []
    try:
        payload = json.loads(lineage_path.read_text(encoding="utf-8"))
    except Exception:
        try:
            payload = parse_yaml(lineage_path.read_text(encoding="utf-8"))
        except Exception:
            return []
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        return [payload]
    return []



def _normalize_newlines(value: str) -> str:
    normalized = value.replace("\r\n", "\n").replace("\r", "\n")
    if not normalized.endswith("\n"):
        normalized += "\n"
    return normalized



def _invalid_console_file_message(filename: str, details: str) -> str:
    return build_guidance_message(
        what=f"{filename} is invalid.",
        why=details,
        fix=f"Update {filename} and retry.",
        example=f"n3 check app.ai",
    )


__all__ = ["get_console_payload", "save_console_payload", "validate_console_payload"]
