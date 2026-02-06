from __future__ import annotations

from pathlib import Path

from namel3ss.quality import run_quality_checks, suggest_quality_fixes
from namel3ss.runtime.capabilities.feature_gate import require_app_capability


def get_quality_payload(source: str, app_path: str) -> dict[str, object]:
    app_file = Path(app_path)
    require_app_capability(app_file, "versioning_quality_mlops", source_override=source)
    report = run_quality_checks(source, project_root=app_file.parent, app_path=app_file)
    report["fixes"] = suggest_quality_fixes(report)
    return report


def apply_quality_payload(source: str, body: dict, app_path: str) -> dict[str, object]:
    _ = body
    return get_quality_payload(source, app_path)


__all__ = ["apply_quality_payload", "get_quality_payload"]
