from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.packs.layout import trust_policy_path
from namel3ss.runtime.packs.risk import risk_rank


DEFAULT_ALLOWED_CAPABILITIES = {
    "filesystem": "write",
    "network": "outbound",
    "env": "read",
    "subprocess": "allow",
}
DEFAULT_MAX_RISK = "high"
CAPABILITY_LEVELS = {
    "filesystem": ["none", "read", "write"],
    "network": ["none", "outbound"],
    "env": ["none", "read"],
    "subprocess": ["none", "allow"],
}


@dataclass(frozen=True)
class PackTrustPolicy:
    allow_unverified_installs: bool
    allow_unverified_enable: bool
    max_risk: str
    allowed_capabilities: dict[str, str]
    source_path: Path | None


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reasons: list[str]


def load_pack_policy(app_root: Path) -> PackTrustPolicy:
    path = trust_policy_path(app_root)
    if not path.exists():
        return PackTrustPolicy(
            allow_unverified_installs=False,
            allow_unverified_enable=False,
            max_risk=DEFAULT_MAX_RISK,
            allowed_capabilities=dict(DEFAULT_ALLOWED_CAPABILITIES),
            source_path=None,
        )
    data = _parse_policy_toml(path)
    allow_installs = _bool_value(data.get("allow_unverified_installs"), default=False, key="allow_unverified_installs")
    allow_enable = _bool_value(data.get("allow_unverified_enable"), default=False, key="allow_unverified_enable")
    max_risk = _str_value(data.get("max_risk"), default=DEFAULT_MAX_RISK, key="max_risk")
    if max_risk not in {"low", "medium", "high"}:
        raise Namel3ssError(_invalid_policy_value("max_risk", max_risk))
    allowed_caps = _parse_allowed_capabilities(data.get("allowed_capabilities"))
    return PackTrustPolicy(
        allow_unverified_installs=allow_installs,
        allow_unverified_enable=allow_enable,
        max_risk=max_risk,
        allowed_capabilities=allowed_caps,
        source_path=path,
    )


def evaluate_policy(
    policy: PackTrustPolicy,
    *,
    operation: str,
    verified: bool,
    risk: str,
    capabilities: dict[str, object],
) -> PolicyDecision:
    reasons: list[str] = []
    if operation == "install" and not verified and not policy.allow_unverified_installs:
        reasons.append("unverified packs are blocked by policy")
    if operation == "enable" and not verified and not policy.allow_unverified_enable:
        reasons.append("unverified packs cannot be enabled")
    if policy.max_risk and risk_rank(risk) > risk_rank(policy.max_risk):
        reasons.append(f"risk {risk} exceeds max_risk {policy.max_risk}")
    for field, allowed in policy.allowed_capabilities.items():
        actual = capabilities.get(field)
        if not isinstance(actual, str):
            reasons.append(f"capability {field} is missing")
            continue
        if not _capability_allows(field, allowed, actual):
            reasons.append(f"{field}={actual} exceeds allowed {allowed}")
    return PolicyDecision(allowed=not reasons, reasons=reasons)


def policy_denied_message(pack_id: str, operation: str, reasons: list[str]) -> str:
    reason_text = "; ".join(reasons) if reasons else "policy denied the request"
    return build_guidance_message(
        what=f'Pack "{pack_id}" is blocked by policy.',
        why=reason_text,
        fix="Update trust policy or choose a different pack.",
        example=f"n3 packs {operation} {pack_id}",
    )


def _capability_allows(field: str, allowed: str, actual: str) -> bool:
    levels = CAPABILITY_LEVELS.get(field)
    if not levels or allowed not in levels or actual not in levels:
        return False
    return levels.index(actual) <= levels.index(allowed)


def _parse_policy_toml(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    try:
        import tomllib  # type: ignore

        data = tomllib.loads(text)
        return data if isinstance(data, dict) else {}
    except Exception:
        return _parse_policy_toml_minimal(text, path)


def _parse_policy_toml_minimal(text: str, path: Path) -> dict[str, object]:
    data: dict[str, object] = {}
    line_no = 0
    for raw_line in text.splitlines():
        line_no += 1
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        if line.startswith("["):
            raise Namel3ssError(_invalid_policy_format(path, line_no))
        if "=" not in line:
            raise Namel3ssError(_invalid_policy_format(path, line_no))
        key, value = line.split("=", 1)
        data[key.strip()] = _parse_policy_value(value.strip(), path, line_no)
    return data


def _parse_policy_value(value: str, path: Path, line_no: int) -> object:
    lowered = value.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    if value.startswith("{") and value.endswith("}"):
        return _parse_inline_table(value[1:-1], path, line_no)
    raise Namel3ssError(_invalid_policy_format(path, line_no))


def _parse_inline_table(text: str, path: Path, line_no: int) -> dict[str, str]:
    if not text.strip():
        return {}
    entries: dict[str, str] = {}
    parts = [part.strip() for part in text.split(",") if part.strip()]
    for part in parts:
        if "=" not in part:
            raise Namel3ssError(_invalid_policy_format(path, line_no))
        key, value = part.split("=", 1)
        key = key.strip().strip('"').strip("'")
        value = value.strip()
        if not key:
            raise Namel3ssError(_invalid_policy_format(path, line_no))
        entries[key] = _strip_quotes(value)
    return entries


def _strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def _parse_allowed_capabilities(value: object) -> dict[str, str]:
    if value is None:
        return dict(DEFAULT_ALLOWED_CAPABILITIES)
    if not isinstance(value, dict):
        raise Namel3ssError(_invalid_policy_value("allowed_capabilities", str(value)))
    allowed = dict(DEFAULT_ALLOWED_CAPABILITIES)
    for key, raw in value.items():
        if not isinstance(key, str) or not isinstance(raw, str):
            raise Namel3ssError(_invalid_policy_value("allowed_capabilities", str(value)))
        if key not in CAPABILITY_LEVELS:
            raise Namel3ssError(_invalid_policy_value("allowed_capabilities", key))
        if raw not in CAPABILITY_LEVELS[key]:
            raise Namel3ssError(_invalid_policy_value("allowed_capabilities", raw))
        allowed[key] = raw
    return allowed


def _bool_value(value: object, *, default: bool, key: str) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    raise Namel3ssError(_invalid_policy_value(key, str(value)))


def _str_value(value: object, *, default: str, key: str) -> str:
    if value is None:
        return default
    if isinstance(value, str):
        return value
    raise Namel3ssError(_invalid_policy_value(key, str(value)))


def _invalid_policy_format(path: Path, line_no: int) -> str:
    return build_guidance_message(
        what="Trust policy file is invalid.",
        why=f"Invalid format at line {line_no} in {path.as_posix()}.",
        fix="Use key = value entries for the policy file.",
        example='allow_unverified_installs = false\\nmax_risk = "medium"',
    )


def _invalid_policy_value(key: str, value: str) -> str:
    return build_guidance_message(
        what=f"Trust policy value for '{key}' is invalid.",
        why=f"Received: {value}.",
        fix="Use valid policy values.",
        example='allowed_capabilities = { network = "outbound" }',
    )


__all__ = [
    "PackTrustPolicy",
    "PolicyDecision",
    "evaluate_policy",
    "load_pack_policy",
    "policy_denied_message",
]
