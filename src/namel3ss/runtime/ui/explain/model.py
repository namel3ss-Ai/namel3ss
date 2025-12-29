from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class UIReason:
    text: str
    kind: str | None = None

    def as_dict(self) -> str:
        return self.text

    @staticmethod
    def from_dict(payload: object) -> "UIReason":
        if isinstance(payload, dict):
            return UIReason(text=str(payload.get("text") or ""), kind=payload.get("kind"))
        return UIReason(text=str(payload or ""))


@dataclass(frozen=True)
class UIElementState:
    id: str
    kind: str
    label: str | None = None
    visible: bool = True
    enabled: bool | None = None
    bound_to: str | None = None
    reasons: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "kind": self.kind,
            "label": self.label,
            "visible": self.visible,
            "enabled": self.enabled,
            "bound_to": self.bound_to,
            "reasons": list(self.reasons),
        }

    @staticmethod
    def from_dict(payload: dict) -> "UIElementState":
        return UIElementState(
            id=str(payload.get("id") or ""),
            kind=str(payload.get("kind") or ""),
            label=payload.get("label"),
            visible=bool(payload.get("visible", True)),
            enabled=payload.get("enabled"),
            bound_to=payload.get("bound_to"),
            reasons=[str(item) for item in payload.get("reasons") or []],
        )


@dataclass(frozen=True)
class UIActionState:
    id: str
    type: str
    status: str
    flow: str | None = None
    record: str | None = None
    requires: str | None = None
    reasons: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "status": self.status,
            "flow": self.flow,
            "record": self.record,
            "requires": self.requires,
            "reasons": list(self.reasons),
        }

    @staticmethod
    def from_dict(payload: dict) -> "UIActionState":
        return UIActionState(
            id=str(payload.get("id") or ""),
            type=str(payload.get("type") or ""),
            status=str(payload.get("status") or ""),
            flow=payload.get("flow"),
            record=payload.get("record"),
            requires=payload.get("requires"),
            reasons=[str(item) for item in payload.get("reasons") or []],
        )


@dataclass(frozen=True)
class UIExplainPack:
    ok: bool
    api_version: str
    pages: list[dict]
    actions: list[dict]
    summary: str
    what_not: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "ok": self.ok,
            "api_version": self.api_version,
            "pages": list(self.pages),
            "actions": list(self.actions),
            "summary": self.summary,
            "what_not": list(self.what_not),
        }

    @staticmethod
    def from_dict(payload: dict) -> "UIExplainPack":
        return UIExplainPack(
            ok=bool(payload.get("ok", True)),
            api_version=str(payload.get("api_version") or ""),
            pages=list(payload.get("pages") or []),
            actions=list(payload.get("actions") or []),
            summary=str(payload.get("summary") or ""),
            what_not=[str(item) for item in payload.get("what_not") or []],
        )


__all__ = ["UIActionState", "UIElementState", "UIExplainPack", "UIReason"]
