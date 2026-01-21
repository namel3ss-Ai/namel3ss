from __future__ import annotations

from namel3ss.cli.targets_store import write_json
from namel3ss.validation import ValidationWarning

BUILD_REPORT_JSON = "build_report.json"
BUILD_REPORT_TEXT = "build_report.txt"


def build_report(
    *,
    build_id: str,
    target: str,
    program_summary: dict,
    artifacts: dict,
    warnings: list[ValidationWarning],
) -> tuple[dict, str]:
    warning_payloads = _normalize_warnings(warnings)
    payload = {
        "schema_version": 1,
        "build_id": build_id,
        "target": target,
        "program_summary": program_summary,
        "artifacts": artifacts,
        "warning_count": len(warning_payloads),
        "warnings": warning_payloads,
    }
    text = _render_build_report(payload)
    return payload, text


def _normalize_warnings(warnings: list[ValidationWarning]) -> list[dict]:
    payloads = [warning.to_dict() for warning in warnings if isinstance(warning, ValidationWarning)]
    return sorted(
        payloads,
        key=lambda item: (
            str(item.get("code") or ""),
            str(item.get("message") or ""),
            str(item.get("path") or ""),
            int(item.get("line") or 0),
            int(item.get("column") or 0),
        ),
    )


def _render_build_report(payload: dict) -> str:
    lines = [
        "Build report",
        "",
        "Build",
        f"- id: {payload.get('build_id')}",
        f"- target: {payload.get('target')}",
        "",
        "Artifacts",
    ]
    artifacts = payload.get("artifacts") if isinstance(payload.get("artifacts"), dict) else {}
    manifest_path = artifacts.get("manifest")
    if manifest_path:
        lines.append(f"- manifest: {manifest_path}")
    ui_paths = artifacts.get("ui") if isinstance(artifacts.get("ui"), dict) else {}
    if ui_paths:
        ui_entries = [ui_paths.get("ui"), ui_paths.get("actions"), ui_paths.get("schema")]
        ui_entries = [entry for entry in ui_entries if entry]
        lines.append(f"- ui contract: {', '.join(ui_entries)}")
    for key in ("program", "config", "lock_snapshot", "program_summary", "entry_instructions", "web"):
        value = artifacts.get(key)
        if value:
            lines.append(f"- {key.replace('_', ' ')}: {value}")
    for key in ("build_report_json", "build_report_text"):
        value = artifacts.get(key)
        if value:
            label = "report json" if key == "build_report_json" else "report text"
            lines.append(f"- {label}: {value}")
    lines.append("")
    lines.append("Warnings")
    warnings = payload.get("warnings") if isinstance(payload.get("warnings"), list) else []
    if not warnings:
        lines.append("- none")
    else:
        for warning in warnings:
            if not isinstance(warning, dict):
                continue
            code = warning.get("code") or "warning"
            message = warning.get("message") or ""
            entry = f"- {code}: {message}".rstrip(": ")
            fix = warning.get("fix")
            if fix:
                entry = f"{entry} (fix: {fix})"
            lines.append(entry)
    return "\n".join(lines).rstrip() + "\n"


def write_build_report(build_path, payload: dict, text: str) -> None:
    write_json(build_path / BUILD_REPORT_JSON, payload)
    (build_path / BUILD_REPORT_TEXT).write_text(text, encoding="utf-8")


__all__ = ["BUILD_REPORT_JSON", "BUILD_REPORT_TEXT", "build_report", "write_build_report"]
