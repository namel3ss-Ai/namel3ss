from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SpecDecision:
    status: str  # compatible | blocked
    declared_spec: str
    engine_supported: tuple[str, ...]
    required_capabilities: tuple[str, ...]
    unsupported_capabilities: tuple[str, ...]
    what: str
    why: tuple[str, ...]
    fix: tuple[str, ...]
    example: str | None

    def as_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "status": self.status,
            "declared_spec": self.declared_spec,
            "engine_supported": list(self.engine_supported),
            "required_capabilities": list(self.required_capabilities),
            "unsupported_capabilities": list(self.unsupported_capabilities),
            "what": self.what,
            "why": list(self.why),
            "fix": list(self.fix),
        }
        if self.example is not None:
            payload["example"] = self.example
        return payload


@dataclass(frozen=True)
class SpecPack:
    decision: SpecDecision
    summary: dict

    def as_dict(self) -> dict[str, object]:
        return {
            "decision": self.decision.as_dict(),
            "summary": dict(self.summary),
        }


__all__ = ["SpecDecision", "SpecPack"]
