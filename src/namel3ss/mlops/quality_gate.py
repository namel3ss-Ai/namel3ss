from __future__ import annotations

from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.quality import run_quality_checks


def validate_model_registration(
    *,
    source: str,
    project_root: str | Path,
    app_path: str | Path,
) -> dict[str, object]:
    report = run_quality_checks(source, project_root=project_root, app_path=app_path)
    if bool(report.get("ok")):
        return report

    issues = report.get("issues")
    first_issue = ""
    if isinstance(issues, list) and issues and isinstance(issues[0], dict):
        first_issue = str(issues[0].get("issue") or "").strip()
    message = _quality_block_message(first_issue)
    raise Namel3ssError(
        message,
        details={
            "http_status": 400,
            "category": "quality",
            "reason_code": "quality_gate_failed",
        },
    )


def _quality_block_message(first_issue: str) -> str:
    hint = f" First issue: {first_issue}" if first_issue else ""
    return build_guidance_message(
        what="Model registration is blocked by quality gates.",
        why=f"The current app failed n3 quality check.{hint}",
        fix="Run n3 quality check, fix issues, then retry model registration.",
        example="n3 quality check",
    )


__all__ = ["validate_model_registration"]
