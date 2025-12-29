from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class RecoveryOption:
    id: str
    title: str
    how: str
    source: str

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "how": self.how,
            "source": self.source,
        }

    @staticmethod
    def from_dict(payload: dict) -> "RecoveryOption":
        return RecoveryOption(
            id=str(payload.get("id") or ""),
            title=str(payload.get("title") or ""),
            how=str(payload.get("how") or ""),
            source=str(payload.get("source") or ""),
        )


@dataclass(frozen=True)
class ErrorWhere:
    flow_name: str | None = None
    step_id: str | None = None
    tool_name: str | None = None

    def as_dict(self) -> dict:
        return {
            "flow_name": self.flow_name,
            "step_id": self.step_id,
            "tool_name": self.tool_name,
        }

    @staticmethod
    def from_dict(payload: dict) -> "ErrorWhere":
        return ErrorWhere(
            flow_name=payload.get("flow_name"),
            step_id=payload.get("step_id"),
            tool_name=payload.get("tool_name"),
        )


@dataclass(frozen=True)
class ErrorState:
    id: str
    kind: str
    where: ErrorWhere
    what: str
    why: str | None = None
    details: dict = field(default_factory=dict)
    impact: list[str] = field(default_factory=list)
    recoverable: bool = False
    recovery_options: list[RecoveryOption] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "kind": self.kind,
            "where": self.where.as_dict(),
            "what": self.what,
            "why": self.why,
            "details": dict(self.details),
            "impact": list(self.impact),
            "recoverable": self.recoverable,
            "recovery_options": [option.as_dict() for option in self.recovery_options],
        }

    @staticmethod
    def from_dict(payload: dict) -> "ErrorState":
        return ErrorState(
            id=str(payload.get("id") or ""),
            kind=str(payload.get("kind") or ""),
            where=ErrorWhere.from_dict(payload.get("where") or {}),
            what=str(payload.get("what") or ""),
            why=payload.get("why"),
            details=dict(payload.get("details") or {}),
            impact=[str(item) for item in payload.get("impact") or []],
            recoverable=bool(payload.get("recoverable", False)),
            recovery_options=[
                RecoveryOption.from_dict(item) for item in payload.get("recovery_options") or [] if isinstance(item, dict)
            ],
        )


__all__ = ["ErrorState", "ErrorWhere", "RecoveryOption"]
