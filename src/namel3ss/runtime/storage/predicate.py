from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class SqlPredicate:
    clause: str
    params: list[Any]


@dataclass(frozen=True)
class PredicatePlan:
    predicate: Callable[[dict], bool]
    sql: SqlPredicate | None = None
    sql_reason: str | None = None


__all__ = ["PredicatePlan", "SqlPredicate"]
