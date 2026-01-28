from __future__ import annotations

from pathlib import Path

from namel3ss.determinism import canonical_json_dumps
from namel3ss.observability.scrub import scrub_payload

from .model import DecisionModel


def build_audit_report(
    model: DecisionModel,
    *,
    project_root: str | Path | None,
    app_path: str | Path | None,
    secret_values: list[str] | None,
) -> dict:
    payload = model.as_dict()
    scrubbed = scrub_payload(
        payload,
        secret_values=secret_values or [],
        project_root=project_root,
        app_path=app_path,
    )
    return scrubbed if isinstance(scrubbed, dict) else {}


def audit_report_json(report: dict, *, pretty: bool = True) -> str:
    return canonical_json_dumps(report, pretty=pretty, drop_run_keys=False)


__all__ = ["audit_report_json", "build_audit_report"]
