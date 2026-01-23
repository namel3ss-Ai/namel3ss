from __future__ import annotations

from dataclasses import dataclass


ActionSignature = tuple[str, str, str | None]
ColumnSignature = tuple[str, str | None]
ListMappingSignature = tuple[tuple[str, str], ...]
GroupSignature = tuple[tuple[str, tuple[str, ...]], ...]


@dataclass(frozen=True)
class ConsistencyLocation:
    page: str
    page_slug: str
    path: str | None
    line: int | None
    column: int | None

    def sort_key(self) -> tuple[str, str, int, int]:
        return (
            self.page_slug or "",
            self.path or "",
            self.line or 0,
            self.column or 0,
        )


@dataclass(frozen=True)
class ConsistencyFinding:
    code: str
    message: str
    fix: str
    record: str
    location: ConsistencyLocation

    def sort_key(self) -> tuple[str, str, str, int, int]:
        path = self.location.path or f"page.{self.location.page_slug}"
        return (
            self.code,
            self.record,
            path or "",
            self.location.line or 0,
            self.location.column or 0,
        )


@dataclass(frozen=True)
class TableConfig:
    columns: tuple[ColumnSignature, ...]
    sort: tuple[str, str] | None
    pagination: int | None
    selection: str | None
    row_actions: tuple[ActionSignature, ...]


@dataclass(frozen=True)
class ListConfig:
    variant: str | None
    item: ListMappingSignature
    selection: str | None
    actions: tuple[ActionSignature, ...]


@dataclass(frozen=True)
class FormConfig:
    groups: GroupSignature
    help_fields: tuple[str, ...]
    readonly_fields: tuple[str, ...]


@dataclass(frozen=True)
class ChartConfig:
    chart_type: str | None
    x: str | None
    y: str | None
    source: str | None
    paired_source: str | None

    def base_signature(self) -> tuple[str | None, str | None, str | None, str | None]:
        return (self.chart_type, self.x, self.y, self.source)


@dataclass(frozen=True)
class ViewConfig:
    representation: str | None


@dataclass(frozen=True)
class RecordAppearance:
    record: str
    component: str
    config: object
    location: ConsistencyLocation
    page_slug: str
    chart_pairing: str | None = None


__all__ = [
    "ActionSignature",
    "ColumnSignature",
    "ConsistencyFinding",
    "ConsistencyLocation",
    "FormConfig",
    "GroupSignature",
    "ListConfig",
    "ListMappingSignature",
    "RecordAppearance",
    "TableConfig",
    "ChartConfig",
    "ViewConfig",
]
