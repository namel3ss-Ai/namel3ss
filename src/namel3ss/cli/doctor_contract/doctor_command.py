from __future__ import annotations

from typing import Any

from namel3ss.cli.doctor_contract.doctor_checks import run_doctor_contract_checks


def append_contract_checks(report: dict[str, Any]) -> dict[str, Any]:
    payload = dict(report or {})
    checks = list(payload.get("checks") or [])
    checks.extend(run_doctor_contract_checks())
    checks = _sorted_checks(checks)
    payload["checks"] = checks
    payload["status"] = _overall_status(checks)
    return payload


def contract_failure_codes(report: dict[str, Any]) -> list[str]:
    checks = list((report or {}).get("checks") or [])
    codes = []
    for check in checks:
        if not isinstance(check, dict):
            continue
        if str(check.get("status") or "") != "error":
            continue
        check_id = str(check.get("id") or "")
        if not check_id.startswith("contract_"):
            continue
        error_code = str(check.get("error_code") or check.get("code") or "").strip()
        if error_code:
            codes.append(error_code)
    return sorted(set(codes))


def _sorted_checks(checks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    order = {
        "environment": 0,
        "project": 1,
        "providers": 2,
        "tools": 3,
        "security": 4,
        "studio": 5,
    }
    return sorted(
        [check for check in checks if isinstance(check, dict)],
        key=lambda item: (
            order.get(str(item.get("category") or "project"), 99),
            str(item.get("id") or ""),
        ),
    )


def _overall_status(checks: list[dict[str, Any]]) -> str:
    statuses = {str(check.get("status") or "") for check in checks if isinstance(check, dict)}
    if "error" in statuses:
        return "error"
    if "warning" in statuses:
        return "warning"
    return "ok"


__all__ = ["append_contract_checks", "contract_failure_codes"]
