from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ToolIntent:
    what: str
    because: str | None = None
    flow_name: str | None = None
    step_id: str | None = None

    def as_dict(self) -> dict:
        return {
            "what": self.what,
            "because": self.because,
            "flow_name": self.flow_name,
            "step_id": self.step_id,
        }

    @staticmethod
    def from_dict(payload: dict) -> "ToolIntent":
        return ToolIntent(
            what=str(payload.get("what") or ""),
            because=payload.get("because"),
            flow_name=payload.get("flow_name"),
            step_id=payload.get("step_id"),
        )


@dataclass(frozen=True)
class ToolPermission:
    allowed: bool | None
    reasons: list[str] = field(default_factory=list)
    capabilities_used: list[str] = field(default_factory=list)
    unsafe_override: bool = False

    def as_dict(self) -> dict:
        return {
            "allowed": self.allowed,
            "reasons": list(self.reasons),
            "capabilities_used": list(self.capabilities_used),
            "unsafe_override": self.unsafe_override,
        }

    @staticmethod
    def from_dict(payload: dict) -> "ToolPermission":
        return ToolPermission(
            allowed=payload.get("allowed"),
            reasons=[str(item) for item in payload.get("reasons") or []],
            capabilities_used=[str(item) for item in payload.get("capabilities_used") or []],
            unsafe_override=bool(payload.get("unsafe_override", False)),
        )


@dataclass(frozen=True)
class ToolEffect:
    duration_ms: int | None = None
    input_summary: str | None = None
    output_summary: str | None = None
    error_type: str | None = None
    error_message: str | None = None

    def as_dict(self) -> dict:
        return {
            "duration_ms": self.duration_ms,
            "input_summary": self.input_summary,
            "output_summary": self.output_summary,
            "error_type": self.error_type,
            "error_message": self.error_message,
        }

    @staticmethod
    def from_dict(payload: dict) -> "ToolEffect":
        return ToolEffect(
            duration_ms=payload.get("duration_ms"),
            input_summary=payload.get("input_summary"),
            output_summary=payload.get("output_summary"),
            error_type=payload.get("error_type"),
            error_message=payload.get("error_message"),
        )


@dataclass(frozen=True)
class ToolDecision:
    id: str
    tool_name: str
    status: str
    intent: ToolIntent
    permission: ToolPermission
    effect: ToolEffect
    details: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "tool_name": self.tool_name,
            "status": self.status,
            "intent": self.intent.as_dict(),
            "permission": self.permission.as_dict(),
            "effect": self.effect.as_dict(),
            "details": dict(self.details),
        }

    @staticmethod
    def from_dict(payload: dict) -> "ToolDecision":
        return ToolDecision(
            id=str(payload.get("id") or ""),
            tool_name=str(payload.get("tool_name") or ""),
            status=str(payload.get("status") or ""),
            intent=ToolIntent.from_dict(payload.get("intent") or {}),
            permission=ToolPermission.from_dict(payload.get("permission") or {}),
            effect=ToolEffect.from_dict(payload.get("effect") or {}),
            details=dict(payload.get("details") or {}),
        )


__all__ = ["ToolDecision", "ToolEffect", "ToolIntent", "ToolPermission"]
