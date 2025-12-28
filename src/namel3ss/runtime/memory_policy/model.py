from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from namel3ss.runtime.memory_trust.model import TrustRules

RETENTION_NEVER = "never"
RETENTION_TTL = "ttl"
RETENTION_DECAY = "decay"

WRITE_POLICY_NONE = "none"
WRITE_POLICY_MINIMAL = "minimal"
WRITE_POLICY_NORMAL = "normal"
WRITE_POLICY_AGGRESSIVE = "aggressive"

AUTHORITY_SYSTEM = "system_imposed"
AUTHORITY_TOOL = "tool_verified"
AUTHORITY_USER = "user_asserted"
AUTHORITY_AI = "ai_inferred"


@dataclass(frozen=True)
class RetentionRule:
    mode: str
    ttl_ticks: Optional[int] = None

    def as_dict(self) -> dict:
        return {"mode": self.mode, "ttl_ticks": self.ttl_ticks}


@dataclass(frozen=True)
class PromotionRule:
    allowed_event_types: List[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {"allowed_event_types": list(self.allowed_event_types)}


@dataclass(frozen=True)
class SpacePromotionRule:
    from_space: str
    to_space: str
    allowed_event_types: List[str] = field(default_factory=list)
    min_authority: str = AUTHORITY_USER
    decision_override: bool = False

    def as_dict(self) -> dict:
        return {
            "from_space": self.from_space,
            "to_space": self.to_space,
            "allowed_event_types": list(self.allowed_event_types),
            "min_authority": self.min_authority,
            "decision_override": self.decision_override,
        }


@dataclass(frozen=True)
class SpacePolicy:
    read_order: List[str] = field(default_factory=list)
    write_spaces: List[str] = field(default_factory=list)
    promotions: List[SpacePromotionRule] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "read_order": list(self.read_order),
            "write_spaces": list(self.write_spaces),
            "promotions": [rule.as_dict() for rule in self.promotions],
        }


@dataclass(frozen=True)
class PhasePolicy:
    enabled: bool = True
    mode: str = "current_only"
    allow_cross_phase_recall: bool = False
    max_phases: Optional[int] = None
    diff_enabled: bool = True

    def as_dict(self) -> dict:
        return {
            "enabled": bool(self.enabled),
            "mode": self.mode,
            "allow_cross_phase_recall": bool(self.allow_cross_phase_recall),
            "max_phases": self.max_phases,
            "diff_enabled": bool(self.diff_enabled),
        }


@dataclass(frozen=True)
class LanePolicy:
    read_order: List[str] = field(default_factory=list)
    write_lanes: List[str] = field(default_factory=list)
    team_enabled: bool = True
    system_enabled: bool = True
    agent_enabled: bool = True
    team_event_types: List[str] = field(default_factory=list)
    team_can_change: bool = True

    def as_dict(self) -> dict:
        return {
            "read_order": list(self.read_order),
            "write_lanes": list(self.write_lanes),
            "team_enabled": bool(self.team_enabled),
            "system_enabled": bool(self.system_enabled),
            "agent_enabled": bool(self.agent_enabled),
            "team_event_types": list(self.team_event_types),
            "team_can_change": bool(self.team_can_change),
        }


@dataclass(frozen=True)
class PrivacyRule:
    deny_patterns: List[str] = field(default_factory=list)
    allow_profile_keys: List[str] = field(default_factory=list)
    deny_sensitive: bool = True

    def as_dict(self) -> dict:
        return {
            "deny_patterns": list(self.deny_patterns),
            "allow_profile_keys": list(self.allow_profile_keys),
            "deny_sensitive": self.deny_sensitive,
        }


@dataclass(frozen=True)
class MemoryPolicyContract:
    write_policy: str
    allow_event_types: List[str] = field(default_factory=list)
    deny_event_types: List[str] = field(default_factory=list)
    retention: Dict[str, Dict[str, RetentionRule]] = field(default_factory=dict)
    promotion: Dict[str, PromotionRule] = field(default_factory=dict)
    privacy: PrivacyRule = field(default_factory=PrivacyRule)
    authority_order: List[str] = field(default_factory=list)
    spaces: SpacePolicy = field(default_factory=SpacePolicy)
    phase: PhasePolicy = field(default_factory=PhasePolicy)
    lanes: LanePolicy = field(default_factory=LanePolicy)
    trust: TrustRules = field(default_factory=TrustRules)

    def as_dict(self) -> dict:
        retention = {
            kind: {event: rule.as_dict() for event, rule in rules.items()} for kind, rules in self.retention.items()
        }
        promotion = {kind: rule.as_dict() for kind, rule in self.promotion.items()}
        return {
            "write_policy": self.write_policy,
            "allow_event_types": list(self.allow_event_types),
            "deny_event_types": list(self.deny_event_types),
            "retention": retention,
            "promotion": promotion,
            "privacy": self.privacy.as_dict(),
            "authority_order": list(self.authority_order),
            "spaces": self.spaces.as_dict(),
            "phase": self.phase.as_dict(),
            "lanes": self.lanes.as_dict(),
            "trust": self.trust.as_dict(),
        }


__all__ = [
    "AUTHORITY_AI",
    "AUTHORITY_SYSTEM",
    "AUTHORITY_TOOL",
    "AUTHORITY_USER",
    "LanePolicy",
    "MemoryPolicyContract",
    "PhasePolicy",
    "PrivacyRule",
    "PromotionRule",
    "SpacePolicy",
    "SpacePromotionRule",
    "RetentionRule",
    "RETENTION_DECAY",
    "RETENTION_NEVER",
    "RETENTION_TTL",
    "WRITE_POLICY_AGGRESSIVE",
    "WRITE_POLICY_MINIMAL",
    "WRITE_POLICY_NONE",
    "WRITE_POLICY_NORMAL",
]
