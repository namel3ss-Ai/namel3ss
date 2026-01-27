from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.ingestion.normalize import preview_text
from namel3ss.ingestion.store import drop_index, store_report


_SIGNAL_ORDER = (
    "text_chars",
    "unique_token_ratio",
    "non_ascii_ratio",
    "line_break_ratio",
    "repeated_line_ratio",
    "table_like_ratio",
    "empty_pages_ratio",
)


def build_ingestion_review(
    state: dict,
    *,
    upload_id: str | None = None,
    project_root: str | None = None,
    app_path: str | None = None,
    secret_values: list[str] | None = None,
) -> dict:
    if not isinstance(state, dict):
        raise Namel3ssError(_state_type_message())
    ingestion = state.get("ingestion")
    if not isinstance(ingestion, dict):
        return {"reports": []}
    ids = sorted(str(key) for key in ingestion.keys())
    if upload_id:
        ids = [uid for uid in ids if uid == upload_id]
    reports: list[dict] = []
    for uid in ids:
        report = ingestion.get(uid)
        if not isinstance(report, dict):
            continue
        status = _normalize_status(report.get("status"))
        reasons = _normalize_reasons(report.get("reasons"))
        signals = _normalize_signals(report.get("signals"))
        method_used = _normalize_method(report.get("method_used"))
        preview_source = report.get("preview") if isinstance(report.get("preview"), str) else ""
        preview = preview_text(
            preview_source,
            project_root=project_root,
            app_path=app_path,
            secret_values=secret_values,
        )
        reports.append(
            {
                "upload_id": uid,
                "status": status,
                "method_used": method_used,
                "signals": signals,
                "reasons": reasons,
                "preview": preview,
            }
        )
    return {"reports": reports}


def apply_ingestion_skip(
    state: dict,
    *,
    upload_id: str,
    project_root: str | None = None,
    app_path: str | None = None,
    secret_values: list[str] | None = None,
) -> dict:
    if not isinstance(upload_id, str) or not upload_id.strip():
        raise Namel3ssError(_upload_id_message())
    if not isinstance(state, dict):
        raise Namel3ssError(_state_type_message())
    ingestion = state.get("ingestion")
    if not isinstance(ingestion, dict) or upload_id not in ingestion:
        raise Namel3ssError(_missing_report_message(upload_id))
    current = ingestion.get(upload_id)
    if not isinstance(current, dict):
        raise Namel3ssError(_missing_report_message(upload_id))
    status = _normalize_status(current.get("status"))
    if status == "pass":
        raise Namel3ssError(_skip_not_allowed_message(upload_id))
    base_reasons = _normalize_reasons(current.get("reasons"))
    reasons = ["skipped"] + [reason for reason in base_reasons if reason != "skipped"]
    preview_source = current.get("preview") if isinstance(current.get("preview"), str) else ""
    preview = preview_text(
        preview_source,
        project_root=project_root,
        app_path=app_path,
        secret_values=secret_values,
    )
    report = {
        "upload_id": upload_id,
        "status": "block",
        "method_used": "skip",
        "signals": _normalize_signals(current.get("signals")),
        "reasons": reasons,
        "preview": preview,
    }
    store_report(state, upload_id=upload_id, report=report)
    drop_index(state, upload_id=upload_id)
    return report


def _normalize_status(value: object) -> str:
    if value in {"pass", "warn", "block"}:
        return str(value)
    return "block"


def _normalize_method(value: object) -> str:
    if isinstance(value, str) and value:
        return value
    return ""


def _normalize_reasons(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str) and item]


def _normalize_signals(value: object) -> dict:
    raw = value if isinstance(value, dict) else {}
    signals: dict[str, float | int] = {}
    for key in _SIGNAL_ORDER:
        if key == "text_chars":
            signals[key] = _coerce_int(raw.get(key))
        else:
            signals[key] = _coerce_float(raw.get(key))
    return signals


def _coerce_int(value: object) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return max(value, 0)
    try:
        return max(int(float(value)), 0)
    except Exception:
        return 0


def _coerce_float(value: object) -> float:
    if isinstance(value, bool):
        return 0.0
    try:
        return round(float(value), 6)
    except Exception:
        return 0.0


def _state_type_message() -> str:
    return build_guidance_message(
        what="State must be an object.",
        why="Ingestion review reads reports from state.ingestion.",
        fix="Ensure state is a JSON object.",
        example='{"ingestion":{}}',
    )


def _upload_id_message() -> str:
    return build_guidance_message(
        what="Ingestion skip requires an upload_id.",
        why="Skipping targets a specific ingestion report.",
        fix="Provide the upload checksum.",
        example='{"upload_id":"<checksum>"}',
    )


def _missing_report_message(upload_id: str) -> str:
    return build_guidance_message(
        what=f"Ingestion report '{upload_id}' was not found.",
        why="Skipping requires an existing ingestion report.",
        fix="Run ingestion first for the upload.",
        example='{"upload_id":"<checksum>"}',
    )


def _skip_not_allowed_message(upload_id: str) -> str:
    return build_guidance_message(
        what=f"Ingestion skip is not allowed for pass reports ({upload_id}).",
        why="Skip is intended for warn or block reports.",
        fix="Use ingestion_run to reprocess or leave the pass report unchanged.",
        example='{"upload_id":"<checksum>","mode":"primary"}',
    )


__all__ = ["apply_ingestion_skip", "build_ingestion_review"]
