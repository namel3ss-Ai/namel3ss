from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from namel3ss.runtime.packs.policy import PackTrustPolicy, evaluate_policy
from namel3ss.runtime.registry.model import entry_risk, entry_trusted, normalize_entry


@dataclass(frozen=True)
class TrustDecision:
    status: str
    verified: bool
    policy_status: str
    policy_reasons: list[str]
    policy_source: str | None


def evaluate_registry_trust(
    entry: dict[str, object],
    *,
    policy: PackTrustPolicy,
    app_root: Path | None,
) -> TrustDecision:
    normalized = normalize_entry(entry)
    verified = entry_trusted(normalized)
    risk = entry_risk(normalized)
    decision = evaluate_policy(
        policy,
        operation="install",
        verified=verified,
        risk=risk,
        capabilities=normalized.get("capabilities", {}),
        pack_id=_str_or_none(normalized.get("pack_id")),
        signer_id=_str_or_none(normalized.get("signer_id")),
    )
    policy_source = _normalize_policy_source(policy.source_path, app_root)
    if decision.allowed:
        reasons = _allowed_reasons(normalized, verified, risk, policy)
        status = "trusted" if verified else "untrusted"
        return TrustDecision(
            status=status,
            verified=verified,
            policy_status="allowed",
            policy_reasons=reasons,
            policy_source=policy_source,
        )
    return TrustDecision(
        status="blocked",
        verified=verified,
        policy_status="blocked",
        policy_reasons=list(decision.reasons),
        policy_source=policy_source,
    )


def _allowed_reasons(entry: dict[str, object], verified: bool, risk: str, policy: PackTrustPolicy) -> list[str]:
    reasons: list[str] = []
    if verified:
        reasons.append("verified signature")
    else:
        reasons.append("unverified allowed by policy")
    reasons.append(f"risk {risk} within policy")
    reasons.append("capabilities within policy")
    if policy.allowed_packs is not None:
        pack_id = _str_or_none(entry.get("pack_id"))
        if pack_id and pack_id in policy.allowed_packs:
            reasons.append("pack id allowed by policy")
    if policy.allowed_signers is not None:
        signer_id = _str_or_none(entry.get("signer_id"))
        if signer_id and signer_id in policy.allowed_signers:
            reasons.append("signer allowed by policy")
    return reasons


def _normalize_policy_source(source: Path | None, app_root: Path | None) -> str | None:
    if source is None:
        return "default"
    try:
        path = source if isinstance(source, Path) else Path(str(source))
    except Exception:
        return None
    if app_root is not None:
        try:
            relative = path.resolve().relative_to(app_root.resolve())
            return relative.as_posix()
        except Exception:
            pass
    return path.name or None


def _str_or_none(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value
    return None


__all__ = ["TrustDecision", "evaluate_registry_trust"]
