from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VerifyCheck:
    id: str
    status: str
    message: str
    fix: str
    details: dict | None = None


def check_to_dict(check: VerifyCheck) -> dict:
    payload = {"id": check.id, "status": check.status, "message": check.message, "fix": check.fix}
    if check.details:
        payload["details"] = check.details
    return payload


__all__ = ["VerifyCheck", "check_to_dict"]
