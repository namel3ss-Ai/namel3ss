from __future__ import annotations

from dataclasses import dataclass


TRUST_VIEWER = "viewer"
TRUST_CONTRIBUTOR = "contributor"
TRUST_APPROVER = "approver"
TRUST_OWNER = "owner"

TRUST_LEVELS = [TRUST_VIEWER, TRUST_CONTRIBUTOR, TRUST_APPROVER, TRUST_OWNER]
TRUST_ORDER = {level: idx for idx, level in enumerate(TRUST_LEVELS)}

_ROLE_TO_TRUST = {
    "owner": TRUST_OWNER,
    "admin": TRUST_OWNER,
    "lead": TRUST_OWNER,
    "approver": TRUST_APPROVER,
    "reviewer": TRUST_APPROVER,
    "manager": TRUST_APPROVER,
    "contributor": TRUST_CONTRIBUTOR,
    "member": TRUST_CONTRIBUTOR,
    "writer": TRUST_CONTRIBUTOR,
    "editor": TRUST_CONTRIBUTOR,
    "verified": TRUST_CONTRIBUTOR,
    "internal": TRUST_APPROVER,
    "guest": TRUST_VIEWER,
    "viewer": TRUST_VIEWER,
    "read": TRUST_VIEWER,
}


@dataclass(frozen=True)
class TrustRules:
    who_can_propose: str = TRUST_CONTRIBUTOR
    who_can_approve: str = TRUST_APPROVER
    who_can_reject: str = TRUST_APPROVER
    approval_count_required: int = 1
    owner_override: bool = True

    def as_dict(self) -> dict:
        return {
            "who_can_propose": self.who_can_propose,
            "who_can_approve": self.who_can_approve,
            "who_can_reject": self.who_can_reject,
            "approval_count_required": int(self.approval_count_required),
            "owner_override": bool(self.owner_override),
        }


def trust_level_from_identity(identity: dict | None) -> str:
    if not isinstance(identity, dict):
        return TRUST_VIEWER
    trust_value = identity.get("trust_level")
    level = _normalize_level(trust_value)
    if level:
        return level
    role_value = identity.get("role")
    level = _normalize_level(role_value)
    if level:
        return level
    return TRUST_VIEWER


def actor_id_from_identity(identity: dict | None) -> str:
    if not isinstance(identity, dict):
        return "anonymous"
    for key in ("id", "user_id", "email", "name"):
        value = identity.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    role_value = identity.get("role")
    if isinstance(role_value, str) and role_value.strip():
        return role_value.strip()
    return "anonymous"


def _normalize_level(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip().lower()
    if not text:
        return None
    if text in TRUST_LEVELS:
        return text
    return _ROLE_TO_TRUST.get(text)


__all__ = [
    "TRUST_APPROVER",
    "TRUST_CONTRIBUTOR",
    "TRUST_LEVELS",
    "TRUST_ORDER",
    "TRUST_OWNER",
    "TRUST_VIEWER",
    "TrustRules",
    "actor_id_from_identity",
    "trust_level_from_identity",
]
