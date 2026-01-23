from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


_COMPONENT_TYPES = {"table", "list", "form", "chart", "view", "chat"}
_CONFIG_COMPONENTS = {"table", "list", "form", "chart"}
_REPRESENTATION_COMPONENTS = {"table", "list", "view"}

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
        path = self.location.path or _page_path(self.location.page_slug)
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


def collect_consistency_findings(pages: list[dict]) -> list[ConsistencyFinding]:
    appearances = _collect_record_appearances(pages)
    findings: list[ConsistencyFinding] = []
    record_pages: dict[str, set[str]] = {
        record: {entry.page_slug for entry in entries} for record, entries in appearances.items()
    }

    for record_name in sorted(appearances):
        entries = appearances[record_name]
        if len(record_pages.get(record_name, set())) <= 1:
            continue

        page_components: dict[str, set[str]] = {}
        for entry in entries:
            if entry.component not in _REPRESENTATION_COMPONENTS:
                continue
            page_components.setdefault(entry.page_slug, set()).add(entry.component)
        unique_sets = {tuple(sorted(values)) for values in page_components.values() if values}
        if len(unique_sets) > 1:
            component_types = sorted({item for values in unique_sets for item in values})
            rep_locations = [entry.location for entry in entries if entry.component in _REPRESENTATION_COMPONENTS]
            findings.append(
                rule_mixed_component_types(
                    record_name=record_name,
                    component_types=component_types,
                    location=_pick_location(rep_locations or [entry.location for entry in entries]),
                )
            )

        component_groups: dict[str, list[RecordAppearance]] = {}
        for entry in entries:
            component_groups.setdefault(entry.component, []).append(entry)

        for component in sorted(component_groups):
            if component not in _CONFIG_COMPONENTS:
                continue
            configs = _configurations_for_component(component, component_groups[component])
            if len(configs) <= 1:
                continue
            if _configurations_additive(component, configs):
                continue
            findings.append(
                rule_inconsistent_configuration(
                    record_name=record_name,
                    component_type=component,
                    location=_pick_location([entry.location for entry in component_groups[component]]),
                )
            )

        chart_entries = [entry for entry in entries if entry.component == "chart"]
        if len({entry.page_slug for entry in chart_entries}) <= 1:
            continue
        pairings = sorted({entry.chart_pairing for entry in chart_entries if entry.chart_pairing})
        if len(pairings) > 1:
            findings.append(
                rule_chart_pairing_inconsistent(
                    record_name=record_name,
                    pairings=pairings,
                    location=_pick_location([entry.location for entry in chart_entries]),
                )
            )

    return findings


def rule_mixed_component_types(
    *,
    record_name: str,
    component_types: list[str],
    location: ConsistencyLocation,
) -> ConsistencyFinding:
    joined = ", ".join(component_types)
    return ConsistencyFinding(
        code="consistency.record_component_type",
        message=f'Record "{record_name}" appears with mixed component types across pages: {joined}.',
        fix="Use a single component type for this record across pages.",
        record=record_name,
        location=location,
    )


def rule_inconsistent_configuration(
    *,
    record_name: str,
    component_type: str,
    location: ConsistencyLocation,
) -> ConsistencyFinding:
    return ConsistencyFinding(
        code="consistency.record_configuration",
        message=f'Record "{record_name}" uses inconsistent {component_type} configuration across pages.',
        fix=_configuration_fix(component_type),
        record=record_name,
        location=location,
    )


def rule_chart_pairing_inconsistent(
    *,
    record_name: str,
    pairings: list[str],
    location: ConsistencyLocation,
) -> ConsistencyFinding:
    joined = ", ".join(pairings)
    return ConsistencyFinding(
        code="consistency.chart_pairing",
        message=f'Record "{record_name}" charts pair with inconsistent sources across pages: {joined}.',
        fix="Pair charts for this record with the same source type (table or list) across pages.",
        record=record_name,
        location=location,
    )


def _configuration_fix(component_type: str) -> str:
    if component_type == "table":
        return "Align table columns, sorting, pagination, selection, and row actions across pages."
    if component_type == "list":
        return "Align list variants, item mappings, selection, and actions across pages."
    if component_type == "form":
        return "Align form groups, help, and readonly flags across pages."
    if component_type == "chart":
        return "Align chart types and mappings across pages."
    return "Align component configuration for this record across pages."


def _collect_record_appearances(pages: list[dict]) -> dict[str, list[RecordAppearance]]:
    appearances: dict[str, list[RecordAppearance]] = {}
    for page in pages:
        page_name = str(page.get("name") or page.get("slug") or "page")
        page_slug = str(page.get("slug") or page_name)
        elements = page.get("elements") or []
        record_sources = _collect_page_sources(elements)

        for element in _walk_elements(elements):
            component = _component_type(element)
            record = _record_name(element)
            if not record or not component:
                continue
            location = _element_location(page_name, page_slug, element)
            chart_pairing = None
            if component == "table":
                config = _table_config(element)
            elif component == "list":
                config = _list_config(element)
            elif component == "form":
                config = _form_config(element)
            elif component == "chart":
                chart_pairing = _paired_source_type(record_sources.get(record, set()))
                config = _chart_config(element, record, chart_pairing)
            elif component == "view":
                config = _view_config(element)
            else:
                config = None
            appearances.setdefault(record, []).append(
                RecordAppearance(
                    record=record,
                    component=component,
                    config=config,
                    location=location,
                    page_slug=page_slug,
                    chart_pairing=chart_pairing,
                )
            )
    return appearances


def _collect_page_sources(elements: list[dict]) -> dict[str, set[str]]:
    sources: dict[str, set[str]] = {}
    for element in _walk_elements(elements):
        element_type = element.get("type")
        if element_type not in {"table", "list"}:
            continue
        record = _record_name(element)
        if not record:
            continue
        sources.setdefault(record, set()).add(str(element_type))
    return sources


def _walk_elements(elements: list[dict]) -> Iterable[dict]:
    for element in elements:
        if not isinstance(element, dict):
            continue
        yield element
        children = element.get("children")
        if isinstance(children, list):
            yield from _walk_elements(children)


def _component_type(element: dict) -> str | None:
    element_type = element.get("type")
    if element_type in _COMPONENT_TYPES:
        return str(element_type)
    return None


def _record_name(element: dict) -> str | None:
    record = element.get("record")
    if isinstance(record, str) and record:
        return record
    return None


def _table_config(element: dict) -> TableConfig:
    return TableConfig(
        columns=_table_columns_signature(element.get("columns")),
        sort=_table_sort_signature(element.get("sort")),
        pagination=_table_pagination_signature(element.get("pagination")),
        selection=_string_or_none(element.get("selection")),
        row_actions=_actions_signature(element.get("row_actions")),
    )


def _list_config(element: dict) -> ListConfig:
    return ListConfig(
        variant=_string_or_none(element.get("variant")),
        item=_list_item_signature(element.get("item")),
        selection=_string_or_none(element.get("selection")),
        actions=_actions_signature(element.get("actions")),
    )


def _form_config(element: dict) -> FormConfig:
    groups = _form_groups_signature(element.get("groups"))
    help_fields, readonly_fields = _form_field_flags(element.get("fields"))
    return FormConfig(groups=groups, help_fields=help_fields, readonly_fields=readonly_fields)


def _chart_config(element: dict, record: str, pairing: str | None) -> ChartConfig:
    source = _string_or_none(element.get("source"))
    if source is None:
        source = record
    return ChartConfig(
        chart_type=_string_or_none(element.get("chart_type")),
        x=_string_or_none(element.get("x")),
        y=_string_or_none(element.get("y")),
        source=source,
        paired_source=pairing,
    )


def _view_config(element: dict) -> ViewConfig:
    return ViewConfig(representation=_string_or_none(element.get("representation")))


def _configurations_for_component(component: str, entries: list[RecordAppearance]) -> list[object]:
    if component == "chart":
        configs = {_chart_signature(entry.config) for entry in entries}
        return list(configs)
    configs = {entry.config for entry in entries}
    return list(configs)


def _chart_signature(config: object) -> tuple[str | None, str | None, str | None, str | None]:
    if isinstance(config, ChartConfig):
        return config.base_signature()
    return (None, None, None, None)


def _configurations_additive(component: str, configs: list[object]) -> bool:
    if component == "table":
        table_configs = [cfg for cfg in configs if isinstance(cfg, TableConfig)]
        if len(table_configs) != len(configs):
            return False
        return _configs_nested(table_configs, _table_config_subset)
    if component == "list":
        list_configs = [cfg for cfg in configs if isinstance(cfg, ListConfig)]
        if len(list_configs) != len(configs):
            return False
        return _configs_nested(list_configs, _list_config_subset)
    return False


def _configs_nested(configs: list[object], subset_fn) -> bool:
    for left in configs:
        for right in configs:
            if left == right:
                continue
            if not (subset_fn(left, right) or subset_fn(right, left)):
                return False
    return True


def _table_config_subset(left: TableConfig, right: TableConfig) -> bool:
    if left.sort != right.sort:
        return False
    if left.pagination != right.pagination:
        return False
    if left.selection != right.selection:
        return False
    if not _is_subsequence(left.columns, right.columns):
        return False
    if not _is_subsequence(left.row_actions, right.row_actions):
        return False
    return True


def _list_config_subset(left: ListConfig, right: ListConfig) -> bool:
    if left.variant != right.variant:
        return False
    if left.selection != right.selection:
        return False
    if not _mapping_subset(left.item, right.item):
        return False
    if not _is_subsequence(left.actions, right.actions):
        return False
    return True


def _mapping_subset(left: ListMappingSignature, right: ListMappingSignature) -> bool:
    right_map = dict(right)
    for key, value in left:
        if right_map.get(key) != value:
            return False
    return True


def _is_subsequence(smaller: tuple, larger: tuple) -> bool:
    if not smaller:
        return True
    index = 0
    for item in larger:
        if item == smaller[index]:
            index += 1
            if index == len(smaller):
                return True
    return False


def _table_columns_signature(columns: object) -> tuple[ColumnSignature, ...]:
    if not isinstance(columns, list):
        return ()
    signature: list[ColumnSignature] = []
    for entry in columns:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name")
        if not isinstance(name, str) or not name:
            continue
        label = entry.get("label")
        label_value = _normalize_text(label)
        signature.append((name, label_value))
    return tuple(signature)


def _table_sort_signature(sort: object) -> tuple[str, str] | None:
    if not isinstance(sort, dict):
        return None
    by = sort.get("by")
    order = sort.get("order")
    if isinstance(by, str) and isinstance(order, str):
        return (by, order)
    return None


def _table_pagination_signature(pagination: object) -> int | None:
    if not isinstance(pagination, dict):
        return None
    page_size = pagination.get("page_size")
    if isinstance(page_size, int):
        return page_size
    return None


def _actions_signature(actions: object) -> tuple[ActionSignature, ...]:
    if not isinstance(actions, list):
        return ()
    entries: list[ActionSignature] = []
    for action in actions:
        if not isinstance(action, dict):
            continue
        label = _normalize_text(action.get("label")) or ""
        if "flow" in action:
            flow = _string_or_none(action.get("flow"))
            entries.append((label, "call_flow", flow))
            continue
        kind = _string_or_none(action.get("type"))
        target = _string_or_none(action.get("target"))
        if kind:
            entries.append((label, kind, target))
    return tuple(entries)


def _list_item_signature(item: object) -> ListMappingSignature:
    if not isinstance(item, dict):
        return ()
    entries: list[tuple[str, str]] = []
    for key in ("primary", "secondary", "meta", "icon"):
        value = item.get(key)
        if isinstance(value, str) and value:
            entries.append((key, value))
    return tuple(entries)


def _form_groups_signature(groups: object) -> GroupSignature:
    if not isinstance(groups, list):
        return ()
    signature: list[tuple[str, tuple[str, ...]]] = []
    for entry in groups:
        if not isinstance(entry, dict):
            continue
        label = _normalize_text(entry.get("label")) or ""
        fields = entry.get("fields")
        field_names: list[str] = []
        if isinstance(fields, list):
            for field in fields:
                if isinstance(field, str) and field:
                    field_names.append(field)
        signature.append((label, tuple(field_names)))
    return tuple(signature)


def _form_field_flags(fields: object) -> tuple[tuple[str, ...], tuple[str, ...]]:
    if not isinstance(fields, list):
        return (), ()
    help_fields: list[str] = []
    readonly_fields: list[str] = []
    for entry in fields:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name")
        if not isinstance(name, str) or not name:
            continue
        help_value = entry.get("help") if "help" in entry else None
        if isinstance(help_value, str) and help_value.strip():
            help_fields.append(name)
        if entry.get("readonly") is True:
            readonly_fields.append(name)
    return tuple(help_fields), tuple(readonly_fields)


def _paired_source_type(types: set[str]) -> str | None:
    if "table" in types and "list" in types:
        return "mixed"
    if "table" in types:
        return "table"
    if "list" in types:
        return "list"
    return None


def _element_location(page_name: str, page_slug: str, element: dict) -> ConsistencyLocation:
    return ConsistencyLocation(
        page=page_name,
        page_slug=page_slug,
        path=element.get("element_id"),
        line=element.get("line"),
        column=element.get("column"),
    )


def _pick_location(locations: list[ConsistencyLocation]) -> ConsistencyLocation:
    if not locations:
        return ConsistencyLocation(page="page", page_slug="page", path=None, line=None, column=None)
    return sorted(locations, key=lambda entry: entry.sort_key())[0]


def _page_path(page_slug: str) -> str:
    return f"page.{page_slug}"


def _string_or_none(value: object) -> str | None:
    if isinstance(value, str) and value:
        return value
    return None


def _normalize_text(value: object) -> str | None:
    if isinstance(value, str):
        trimmed = value.strip()
        return trimmed if trimmed else None
    if value is None:
        return None
    return str(value).strip()


__all__ = ["ConsistencyFinding", "ConsistencyLocation", "collect_consistency_findings"]
