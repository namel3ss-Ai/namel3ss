from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any, Dict

from namel3ss.cli.devex import build_doctor_report, parse_project_overrides, _status_icon
from namel3ss.cli.doctor_models import DoctorCheck
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message


def _print_human(report: Dict[str, Any]) -> None:
    category_labels = {
        "environment": "Environment",
        "project": "Project",
        "providers": "AI providers",
        "tools": "Python tools",
        "security": "Security",
        "studio": "Studio",
    }
    checks_by_category: dict[str, list[dict[str, object]]] = {}
    for check in report.get("checks", []):
        category = str(check.get("category") or "project")
        checks_by_category.setdefault(category, []).append(check)
    for category in category_labels:
        checks = checks_by_category.get(category)
        if not checks:
            continue
        print(f"{category_labels[category]}:")
        for check in checks:
            icon = _status_icon(str(check.get("status", "")))
            message = check.get("message") or ""
            print(f"  {icon} {message}")
            fix = check.get("fix") or ""
            if fix:
                print(f"      Fix: {fix}")


def _print_failure(exc: Exception, json_mode: bool) -> None:
    message = "n3 doctor failed to run. Please report this with the stack trace."
    fix = "Re-run with a clean environment or reinstall namel3ss."
    payload = {
        "status": "error",
        "checks": [
            {"id": "doctor", "status": "error", "message": message, "fix": fix, "error": str(exc)}
        ],
    }
    if json_mode:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"❌ {message}")
        print(f"      Fix: {fix}")
        print(f"      Details: {exc}")


def _report_unknown_args(args: list[str]) -> dict[str, Any]:
    message = build_guidance_message(
        what=f"Unknown doctor arguments: {' '.join(args)}.",
        why="doctor only accepts --json plus optional --app/--project overrides.",
        fix="Remove the extra arguments and re-run.",
        example="n3 doctor --json",
    )
    check = DoctorCheck(
        id="doctor_args",
        category="environment",
        code="doctor.args.invalid",
        status="error",
        message=message,
        fix="Remove unknown arguments.",
    )
    return {"status": "error", "checks": [asdict(check)]}


def run_doctor(args: list[str] | None = None) -> int:
    argv = list(args or [])
    try:
        overrides, remaining = parse_project_overrides(argv)
        json_mode = "--json" in remaining
        tail = [arg for arg in remaining if arg != "--json"]
        if tail:
            report = _report_unknown_args(tail)
            if json_mode:
                print(json.dumps(report, indent=2, sort_keys=True))
            else:
                _print_human(report)
            return 1
        report = build_doctor_report(overrides)
        if json_mode:
            print(json.dumps(report, indent=2, sort_keys=True))
        else:
            _print_human(report)
        return 0
    except Exception as exc:  # pragma: no cover - defensive guard rail
        _print_failure(exc, "--json" in argv)
        return 1


__all__ = ["run_doctor"]
