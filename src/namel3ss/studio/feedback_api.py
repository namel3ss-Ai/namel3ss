from __future__ import annotations

import hashlib
from pathlib import Path

from namel3ss.feedback import append_feedback_entry, load_feedback_entries, summarize_feedback
from namel3ss.retrain import build_retrain_payload, schedule_retrain_jobs, write_retrain_payload
from namel3ss.runtime.ai.canary_results import load_canary_results, summarize_canary_results
from namel3ss.runtime.ai.model_manager import configure_canary
from namel3ss.runtime.ai.models_config import load_models_config



def get_feedback_payload(app_path: str) -> dict[str, object]:
    app_file = Path(app_path)
    entries = load_feedback_entries(app_file.parent, app_file)
    return {
        "ok": True,
        "count": len(entries),
        "summary": summarize_feedback(entries),
        "entries": [entry.to_dict() for entry in entries],
    }



def submit_feedback_payload(source: str, body: dict, app_path: str) -> dict[str, object]:
    _ = source
    app_file = Path(app_path)
    rating = body.get("rating")
    if not isinstance(rating, str) or not rating.strip():
        return {
            "ok": False,
            "error": "rating is required.",
        }
    flow_name = _read_text(body.get("flow_name")) or "unknown_flow"
    input_id = _read_text(body.get("input_id"))
    if not input_id:
        input_text = _read_text(body.get("input_text")) or ""
        input_id = _input_id(input_text)
    comment = _read_text(body.get("comment")) or ""
    raw_step = body.get("step_count")
    step_count = int(raw_step) if isinstance(raw_step, int) else None
    entry = append_feedback_entry(
        app_file.parent,
        app_file,
        flow_name=flow_name,
        input_id=input_id,
        rating=rating,
        comment=comment,
        step_count=step_count,
    )
    return {
        "ok": True,
        "entry": entry.to_dict(),
    }



def get_retrain_payload(app_path: str) -> dict[str, object]:
    app_file = Path(app_path)
    return build_retrain_payload(app_file.parent, app_file)



def schedule_retrain_payload(source: str, body: dict, app_path: str) -> dict[str, object]:
    _ = source
    _ = body
    app_file = Path(app_path)
    payload = schedule_retrain_jobs(app_file.parent, app_file)
    output_path = write_retrain_payload(app_file.parent, app_file)
    payload["output_path"] = output_path.as_posix()
    return payload



def get_canary_payload(app_path: str) -> dict[str, object]:
    app_file = Path(app_path)
    records = load_canary_results(app_file.parent, app_file)
    summary = summarize_canary_results(records)
    models = load_models_config(app_file.parent, app_file)
    return {
        "ok": True,
        "count": len(records),
        "summary": summary,
        "records": records,
        "models": [
            {
                "name": item.name,
                "version": item.version,
                "canary_target": item.canary_target,
                "canary_fraction": item.canary_fraction,
                "shadow_target": item.shadow_target,
            }
            for item in [models.models[name] for name in sorted(models.models.keys())]
        ],
    }



def configure_canary_payload(source: str, body: dict, app_path: str) -> dict[str, object]:
    _ = source
    app_file = Path(app_path)
    primary = _read_text(body.get("primary_model"))
    candidate = _read_text(body.get("candidate_model"))
    shadow = bool(body.get("shadow"))
    raw_fraction = body.get("fraction")
    if not primary:
        return {"ok": False, "error": "primary_model is required."}
    if candidate == "off":
        candidate = ""
    if candidate:
        try:
            fraction = float(raw_fraction)
        except Exception:
            return {"ok": False, "error": "fraction must be a number from 0 to 1."}
    else:
        fraction = 0.0
        shadow = False
    path = configure_canary(
        project_root=app_file.parent,
        app_path=app_file,
        primary_model=primary,
        candidate_model=candidate or None,
        fraction=fraction,
        shadow=shadow,
    )
    return {
        "ok": True,
        "primary_model": primary,
        "candidate_model": candidate or None,
        "fraction": fraction,
        "shadow": shadow,
        "models_path": path.as_posix(),
    }



def _read_text(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()



def _input_id(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()[:12]


__all__ = [
    "configure_canary_payload",
    "get_canary_payload",
    "get_feedback_payload",
    "get_retrain_payload",
    "schedule_retrain_payload",
    "submit_feedback_payload",
]
