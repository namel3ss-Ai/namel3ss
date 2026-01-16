from __future__ import annotations

from typing import Any

from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.contract import build_error_entry


def build_dev_overlay_payload(payload: object, *, debug: bool = False) -> dict:
    error_payload = _coerce_payload(payload)
    entry = build_error_entry(error_payload=error_payload, error=None, error_pack=None)
    summary = _summary_line(entry, error_payload)
    sections = _build_sections(entry)
    overlay = {"title": "something went wrong", "summary": summary, "sections": sections}
    if debug:
        overlay["details"] = _debug_details(error_payload, entry)
    return overlay


def _coerce_payload(payload: object) -> dict:
    if isinstance(payload, dict):
        return dict(payload)
    if isinstance(payload, str):
        return {"ok": False, "error": payload, "message": payload, "kind": "runtime"}
    return {"ok": False, "error": "Unexpected error.", "message": "Unexpected error.", "kind": "runtime"}


def _summary_line(entry: dict, payload: dict) -> str:
    summary = _first_text(entry.get("message"), payload.get("message"), payload.get("error"))
    if not summary:
        summary = "Unexpected error."
    return _ensure_sentence(summary)


def _build_sections(entry: dict) -> list[dict]:
    sections: list[dict] = []
    message = entry.get("message")
    if isinstance(message, str) and message:
        sections.append({"title": "what happened", "body": message})
    hint = entry.get("hint")
    if isinstance(hint, str) and hint:
        sections.append({"title": "why", "body": hint})
    remediation = entry.get("remediation")
    if isinstance(remediation, str) and remediation:
        sections.append({"title": "how to fix", "items": _split_fix(remediation)})
    return sections


def _split_fix(text: str) -> list[str]:
    cleaned = " ".join(text.split())
    if not cleaned:
        return []
    return [cleaned]


def _ensure_sentence(text: str) -> str:
    cleaned = " ".join(text.split())
    if not cleaned:
        return "Unexpected error."
    if cleaned.endswith((".", "!", "?")):
        return cleaned
    return f"{cleaned}."


def _debug_details(payload: dict, entry: dict) -> str:
    debug_payload: dict[str, Any] = {
        "kind": payload.get("kind"),
        "message": payload.get("message") or payload.get("error"),
        "entry": entry,
    }
    return canonical_json_dumps(debug_payload, pretty=True)


def _first_text(*values: object) -> str:
    for value in values:
        if isinstance(value, str):
            cleaned = value.strip()
            if cleaned:
                return cleaned
    return ""


__all__ = ["build_dev_overlay_payload"]
