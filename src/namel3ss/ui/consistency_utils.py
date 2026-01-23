from __future__ import annotations

from namel3ss.ui.consistency_models import (
    ChartConfig,
    ConsistencyLocation,
    ListConfig,
    ListMappingSignature,
    RecordAppearance,
    TableConfig,
)


def _normalize_text(value: object) -> str | None:
    if isinstance(value, str):
        trimmed = value.strip()
        return trimmed if trimmed else None
    if value is None:
        return None
    return str(value).strip()


def _string_or_none(value: object) -> str | None:
    if isinstance(value, str) and value:
        return value
    return None


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


def _chart_signature(config: object) -> tuple[str | None, str | None, str | None, str | None]:
    if isinstance(config, ChartConfig):
        return config.base_signature()
    return (None, None, None, None)


def _configurations_for_component(component: str, entries: list[RecordAppearance]) -> list[object]:
    if component == "chart":
        configs = {_chart_signature(entry.config) for entry in entries}
        return list(configs)
    configs = {entry.config for entry in entries}
    return list(configs)


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


def _pick_location(locations: list[ConsistencyLocation]) -> ConsistencyLocation:
    if not locations:
        return ConsistencyLocation(page="page", page_slug="page", path=None, line=None, column=None)
    return sorted(locations, key=lambda entry: entry.sort_key())[0]


__all__ = [
    "_chart_signature",
    "_configurations_additive",
    "_configurations_for_component",
    "_configs_nested",
    "_is_subsequence",
    "_list_config_subset",
    "_mapping_subset",
    "_normalize_text",
    "_pick_location",
    "_string_or_none",
    "_table_config_subset",
]
