from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class FlowIntent:
    flow_name: str
    purpose: str
    requires: str | None = None
    audited: bool = False
    expected_effects: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "flow_name": self.flow_name,
            "purpose": self.purpose,
            "requires": self.requires,
            "audited": self.audited,
            "expected_effects": list(self.expected_effects),
        }

    @staticmethod
    def from_dict(payload: dict) -> "FlowIntent":
        return FlowIntent(
            flow_name=str(payload.get("flow_name") or ""),
            purpose=str(payload.get("purpose") or ""),
            requires=payload.get("requires"),
            audited=bool(payload.get("audited", False)),
            expected_effects=[str(item) for item in payload.get("expected_effects") or []],
        )


@dataclass(frozen=True)
class FlowOutcome:
    status: str
    returned: bool
    return_summary: str | None = None
    tool_summary: dict = field(default_factory=dict)
    memory_summary: dict = field(default_factory=dict)
    skipped_summary: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "status": self.status,
            "returned": self.returned,
            "return_summary": self.return_summary,
            "tool_summary": dict(self.tool_summary),
            "memory_summary": dict(self.memory_summary),
            "skipped_summary": dict(self.skipped_summary),
        }

    @staticmethod
    def from_dict(payload: dict) -> "FlowOutcome":
        return FlowOutcome(
            status=str(payload.get("status") or ""),
            returned=bool(payload.get("returned", False)),
            return_summary=payload.get("return_summary"),
            tool_summary=dict(payload.get("tool_summary") or {}),
            memory_summary=dict(payload.get("memory_summary") or {}),
            skipped_summary=dict(payload.get("skipped_summary") or {}),
        )


@dataclass(frozen=True)
class FlowSummary:
    intent: FlowIntent
    outcome: FlowOutcome
    reasons: list[str] = field(default_factory=list)
    what_not: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "intent": self.intent.as_dict(),
            "outcome": self.outcome.as_dict(),
            "reasons": list(self.reasons),
            "what_not": list(self.what_not),
        }

    @staticmethod
    def from_dict(payload: dict) -> "FlowSummary":
        return FlowSummary(
            intent=FlowIntent.from_dict(payload.get("intent") or {}),
            outcome=FlowOutcome.from_dict(payload.get("outcome") or {}),
            reasons=[str(item) for item in payload.get("reasons") or []],
            what_not=[str(item) for item in payload.get("what_not") or []],
        )


__all__ = ["FlowIntent", "FlowOutcome", "FlowSummary"]
