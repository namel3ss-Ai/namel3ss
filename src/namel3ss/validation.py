from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, List, Sequence


class ValidationMode(str, Enum):
    STATIC = "static"
    RUNTIME = "runtime"

    @classmethod
    def from_value(cls, value: object | None) -> "ValidationMode":
        if isinstance(value, cls):
            return value
        if value is None:
            return cls.RUNTIME
        if isinstance(value, str):
            lowered = value.lower()
            if lowered in {"static", "runtime"}:
                return cls(lowered)
        raise ValueError(f"Unknown validation mode: {value}")


@dataclass
class ValidationWarning:
    code: str
    message: str
    fix: str | None = None
    path: str | None = None
    line: int | None = None
    column: int | None = None
    category: str = "general"
    enforced_at: str | None = None

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "message": self.message,
            "fix": self.fix,
            "path": self.path,
            "line": self.line,
            "column": self.column,
            "category": self.category,
            "enforced_at": self.enforced_at,
        }


def _derive_category(code: str | None) -> str:
    if not code:
        return "general"
    prefix = code.split(".")[0]
    mapping = {
        "state": "state",
        "identity": "identity",
        "requires": "permissions",
        "actions": "actions",
    }
    return mapping.get(prefix, "general")


def add_warning(
    warnings: list[ValidationWarning] | None,
    *,
    code: str,
    message: str,
    fix: str | None = None,
    path: Sequence[str] | str | None = None,
    line: int | None = None,
    column: int | None = None,
    category: str | None = None,
    enforced_at: str | None = None,
) -> None:
    if warnings is None:
        return
    path_str = ".".join(str(part) for part in path) if isinstance(path, (list, tuple)) else path
    resolved_path = f"state.{path_str}" if path_str and not isinstance(path, str) else path_str
    warnings.append(
        ValidationWarning(
            code=code,
            message=message,
            fix=fix,
            path=resolved_path,
            line=line,
            column=column,
            category=category or _derive_category(code),
            enforced_at=enforced_at,
        )
    )


def add_unique_warning(
    warnings: list[ValidationWarning] | None,
    seen: set[str],
    *,
    code: str,
    message: str,
    fix: str | None = None,
    path: Iterable[str] | str | None = None,
    line: int | None = None,
    column: int | None = None,
    category: str | None = None,
    enforced_at: str | None = None,
) -> None:
    if warnings is None:
        return
    key_parts = [code]
    if isinstance(path, str):
        key_parts.append(path)
    elif path is not None:
        key_parts.append(".".join(path))
    if line is not None:
        key_parts.append(str(line))
    if column is not None:
        key_parts.append(str(column))
    key = "|".join(key_parts)
    if key in seen:
        return
    seen.add(key)
    add_warning(
        warnings,
        code=code,
        message=message,
        fix=fix,
        path=path,
        line=line,
        column=column,
        category=category,
        enforced_at=enforced_at,
    )


__all__ = ["ValidationMode", "ValidationWarning", "add_warning", "add_unique_warning"]
