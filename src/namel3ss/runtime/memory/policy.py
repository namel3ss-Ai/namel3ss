from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

WRITE_POLICIES = {"none", "minimal", "normal", "aggressive"}
FORGET_POLICIES = {"never", "decay", "ttl"}

DEFAULT_SEMANTIC_TOP_K = 3
DEFAULT_WRITE_POLICY = "normal"
DEFAULT_FORGET_POLICY = "decay"
DEFAULT_DEDUPE_ENABLED = True
DEFAULT_SHORT_TERM_TOKEN_BUDGET: Optional[int] = None
DEFAULT_PHASE_ENABLED = True
DEFAULT_PHASE_MODE = "current_only"
DEFAULT_ALLOW_CROSS_PHASE_RECALL = False
DEFAULT_PHASE_MAX = None
DEFAULT_PHASE_DIFF_ENABLED = True


@dataclass(frozen=True)
class MemoryPolicy:
    short_term_max_turns: int
    short_term_token_budget: Optional[int]
    semantic_enabled: bool
    semantic_top_k: int
    profile_enabled: bool
    write_policy: str
    forget_policy: str
    dedupe_enabled: bool
    phase_enabled: bool
    phase_mode: str
    allow_cross_phase_recall: bool
    phase_max_phases: Optional[int]
    phase_diff_enabled: bool

    def as_trace_dict(self) -> dict:
        phase_mode = self.phase_mode
        if self.allow_cross_phase_recall:
            phase_mode = "current_plus_history"
        return {
            "short_term": self.short_term_max_turns,
            "semantic": self.semantic_enabled,
            "profile": self.profile_enabled,
            "short_term_max_turns": self.short_term_max_turns,
            "short_term_token_budget": self.short_term_token_budget,
            "semantic_top_k": self.semantic_top_k,
            "write_policy": self.write_policy,
            "forget_policy": self.forget_policy,
            "dedupe_enabled": self.dedupe_enabled,
            "phase_mode": phase_mode,
            "allow_cross_phase_recall": self.allow_cross_phase_recall,
            "phase_enabled": self.phase_enabled,
            "phase_max_phases": self.phase_max_phases,
            "phase_diff_enabled": self.phase_diff_enabled,
        }


def build_policy(*, short_term: int, semantic: bool, profile: bool) -> MemoryPolicy:
    return MemoryPolicy(
        short_term_max_turns=max(short_term or 0, 0),
        short_term_token_budget=DEFAULT_SHORT_TERM_TOKEN_BUDGET,
        semantic_enabled=bool(semantic),
        semantic_top_k=DEFAULT_SEMANTIC_TOP_K,
        profile_enabled=bool(profile),
        write_policy=DEFAULT_WRITE_POLICY,
        forget_policy=DEFAULT_FORGET_POLICY,
        dedupe_enabled=DEFAULT_DEDUPE_ENABLED,
        phase_enabled=DEFAULT_PHASE_ENABLED,
        phase_mode=DEFAULT_PHASE_MODE,
        allow_cross_phase_recall=DEFAULT_ALLOW_CROSS_PHASE_RECALL,
        phase_max_phases=DEFAULT_PHASE_MAX,
        phase_diff_enabled=DEFAULT_PHASE_DIFF_ENABLED,
    )


__all__ = ["MemoryPolicy", "build_policy", "FORGET_POLICIES", "WRITE_POLICIES"]
