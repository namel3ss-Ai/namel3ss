from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RuntimeWhere:
    """Where the runtime error happened, based on known execution context."""

    flow_name: str | None
    statement_kind: str | None  # stable label like "ask_ai" or "save"
    statement_index: int | None  # 1-based index in the flow body
    line: int | None
    column: int | None

    def as_dict(self) -> dict[str, object]:
        return {
            "flow_name": self.flow_name,
            "statement_kind": self.statement_kind,
            "statement_index": self.statement_index,
            "line": self.line,
            "column": self.column,
        }


@dataclass(frozen=True)
class Namel3ssRuntimeError:
    """Stable runtime error contract for deterministic reporting."""

    error_id: str  # deterministic error id
    kind: str  # stable error kind (not a Python class name)
    boundary: str  # ai | tools | store | memory | theme | fs | engine
    what: str  # one-line summary
    why: tuple[str, ...]  # factual bullets
    fix: tuple[str, ...]  # actionable bullets
    example: str | None
    where: RuntimeWhere
    raw_message: str  # original error message (redacted)

    def as_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "error_id": self.error_id,
            "kind": self.kind,
            "boundary": self.boundary,
            "what": self.what,
            "why": list(self.why),
            "fix": list(self.fix),
            "example": self.example,
            "where": self.where.as_dict(),
            "raw_message": self.raw_message,
        }
        return payload


@dataclass(frozen=True)
class ErrorPack:
    """Error proof pack written on runtime failures."""

    error: Namel3ssRuntimeError
    summary: dict[str, object]  # ok=false, flow_name, boundary, kind
    traces_tail: list[dict]  # optional, redacted tail of traces

    def as_dict(self) -> dict[str, object]:
        return {
            "error": self.error.as_dict(),
            "summary": self.summary,
            "traces_tail": self.traces_tail,
        }


__all__ = ["ErrorPack", "Namel3ssRuntimeError", "RuntimeWhere"]
