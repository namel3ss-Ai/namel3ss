from __future__ import annotations

from namel3ss.ui.consistency_index import _collect_record_appearances
from namel3ss.ui.consistency_models import (
    ConsistencyFinding,
    ConsistencyLocation,
    RecordAppearance,
)
from namel3ss.ui.consistency_utils import (
    _configurations_additive,
    _configurations_for_component,
    _pick_location,
)


_CONFIG_COMPONENTS = {"table", "list", "form", "chart"}
_REPRESENTATION_COMPONENTS = {"table", "list", "view"}


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


__all__ = ["ConsistencyFinding", "ConsistencyLocation", "collect_consistency_findings"]
