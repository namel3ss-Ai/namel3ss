from __future__ import annotations

from typing import Iterable

from namel3ss.ui.consistency_rules import collect_consistency_findings
from namel3ss.ui.copy_rules import collect_copy_findings
from namel3ss.ui.icon_rules import collect_icon_findings
from namel3ss.ui.manifest.page_structure import page_root_elements
from namel3ss.ui.layout_rules import (
    LayoutFinding,
    LayoutLocation,
    container_label,
    is_action_element,
    is_container_type,
    is_data_heavy_element,
    is_labeled_container,
    is_overlay_type,
    record_representation,
    rule_action_heavy_container,
    rule_deep_nesting,
    rule_flat_page_sprawl,
    rule_grid_sprawl,
    rule_inconsistent_columns,
    rule_mixed_record_representation,
    rule_ungrouped_data_heavy,
    rule_unlabeled_container,
)
from namel3ss.ui.story_tone_rules import collect_story_tone_findings
from namel3ss.validation import add_warning


def append_layout_warnings(pages: list[dict], warnings: list | None, context: dict | None = None) -> None:
    del context
    if warnings is None:
        return
    findings = collect_layout_findings(pages)
    for finding in sorted(findings, key=lambda entry: entry.sort_key()):
        location = finding.location
        path = location.path or _page_path(location.page_slug)
        add_warning(
            warnings,
            code=finding.code,
            message=finding.message,
            fix=finding.fix,
            path=path,
            line=location.line,
            column=location.column,
            category="layout",
        )


def append_copy_warnings(pages: list[dict], warnings: list | None, context: dict | None = None) -> None:
    del context
    if warnings is None:
        return
    findings = collect_copy_findings(pages)
    for finding in sorted(findings, key=lambda entry: entry.sort_key()):
        location = finding.location
        path = location.path or _page_path(location.page_slug)
        add_warning(
            warnings,
            code=finding.code,
            message=finding.message,
            fix=finding.fix,
            path=path,
            line=location.line,
            column=location.column,
            category="copy",
        )


def append_visibility_warnings(pages: list[dict], warnings: list | None, context: dict | None = None) -> None:
    del context
    if warnings is None:
        return
    findings = collect_visibility_findings(pages)
    for finding in sorted(findings, key=lambda entry: entry.sort_key()):
        location = finding.location
        path = location.path or _page_path(location.page_slug)
        add_warning(
            warnings,
            code=finding.code,
            message=finding.message,
            fix=finding.fix,
            path=path,
            line=location.line,
            column=location.column,
            category="visibility",
        )


def append_story_icon_warnings(pages: list[dict], warnings: list | None, context: dict | None = None) -> None:
    del context
    if warnings is None:
        return
    findings = list(collect_story_tone_findings(pages))
    findings.extend(collect_icon_findings(pages))
    for finding in sorted(findings, key=_story_icon_sort_key):
        location = finding.location
        path = location.path or _page_path(location.page_slug)
        category = "story" if finding.code.startswith("story.") else "icon"
        add_warning(
            warnings,
            code=finding.code,
            message=finding.message,
            fix=finding.fix,
            path=path,
            line=location.line,
            column=location.column,
            category=category,
        )


def append_story_tone_warnings(pages: list[dict], warnings: list | None, context: dict | None = None) -> None:
    del context
    if warnings is None:
        return
    findings = collect_story_tone_findings(pages)
    for finding in sorted(findings, key=lambda entry: entry.sort_key()):
        location = finding.location
        path = location.path or _page_path(location.page_slug)
        add_warning(
            warnings,
            code=finding.code,
            message=finding.message,
            fix=finding.fix,
            path=path,
            line=location.line,
            column=location.column,
            category="story",
        )


def append_icon_warnings(pages: list[dict], warnings: list | None, context: dict | None = None) -> None:
    del context
    if warnings is None:
        return
    findings = collect_icon_findings(pages)
    for finding in sorted(findings, key=lambda entry: entry.sort_key()):
        location = finding.location
        path = location.path or _page_path(location.page_slug)
        add_warning(
            warnings,
            code=finding.code,
            message=finding.message,
            fix=finding.fix,
            path=path,
            line=location.line,
            column=location.column,
            category="icon",
        )


def append_consistency_warnings(pages: list[dict], warnings: list | None, context: dict | None = None) -> None:
    del context
    if warnings is None:
        return
    findings = collect_consistency_findings(pages)
    for finding in sorted(findings, key=lambda entry: entry.sort_key()):
        location = finding.location
        path = location.path or _page_path(location.page_slug)
        add_warning(
            warnings,
            code=finding.code,
            message=finding.message,
            fix=finding.fix,
            path=path,
            line=location.line,
            column=location.column,
            category="consistency",
        )


def collect_layout_findings(pages: list[dict]) -> list[LayoutFinding]:
    findings: list[LayoutFinding] = []
    record_representations: dict[str, dict[str, list[LayoutLocation]]] = {}
    record_columns: dict[str, dict[tuple[tuple[str, str | None], ...], list[LayoutLocation]]] = {}

    for page in pages:
        page_name = str(page.get("name") or page.get("slug") or "page")
        page_slug = str(page.get("slug") or page_name)
        elements = page_root_elements(page)
        element_count, leaf_count = _page_counts(elements)
        page_location = LayoutLocation(page=page_name, page_slug=page_slug, path=_page_path(page_slug), line=None, column=None)
        flat = rule_flat_page_sprawl(
            page_name=page_name,
            page_slug=page_slug,
            element_count=element_count,
            leaf_count=leaf_count,
            location=page_location,
        )
        if flat:
            findings.append(flat)

        ungrouped_data_heavy = 0

        def walk(children: list[dict], *, depth: int, grouped: bool) -> None:
            nonlocal ungrouped_data_heavy
            for element in children:
                if not isinstance(element, dict):
                    continue
                element_type = element.get("type")
                location = _element_location(page_name, page_slug, element)
                label = container_label(element)
                if element_type in {"card", "compose", "drawer", "modal", "section", "tab"} and not label:
                    findings.append(rule_unlabeled_container(container_type=str(element_type), location=location))

                if is_container_type(element_type):
                    container_depth = depth + 1
                    deep = rule_deep_nesting(
                        container_type=str(element_type),
                        depth=container_depth,
                        location=location,
                    )
                    if deep:
                        findings.append(deep)

                    action_count = _count_actions(element)
                    heavy = rule_action_heavy_container(
                        container_type=str(element_type),
                        label=label,
                        action_count=action_count,
                        location=location,
                    )
                    if heavy:
                        findings.append(heavy)

                    if element_type == "row":
                        column_count = _count_columns(element)
                        grid = rule_grid_sprawl(column_count=column_count, location=location)
                        if grid:
                            findings.append(grid)

                if is_data_heavy_element(element) and not grouped:
                    ungrouped_data_heavy += 1

                record_name = element.get("record")
                representation = record_representation(element)
                if record_name and representation:
                    record_representations.setdefault(record_name, {}).setdefault(representation, []).append(location)

                if element_type == "table" and element.get("columns_configured"):
                    signature = _table_columns_signature(element)
                    if signature and record_name:
                        record_columns.setdefault(record_name, {}).setdefault(signature, []).append(location)

                if is_container_type(element_type):
                    next_grouped = grouped or is_labeled_container(element)
                    nested = element.get("children")
                    if isinstance(nested, list):
                        walk(nested, depth=container_depth, grouped=next_grouped)

        walk(elements, depth=0, grouped=False)

        grouped_warning = rule_ungrouped_data_heavy(
            page_name=page_name,
            page_slug=page_slug,
            count=ungrouped_data_heavy,
            location=page_location,
        )
        if grouped_warning:
            findings.append(grouped_warning)

    findings.extend(_record_representation_findings(record_representations))
    findings.extend(_record_column_findings(record_columns))
    return findings


def collect_visibility_findings(pages: list[dict]) -> list[LayoutFinding]:
    findings: list[LayoutFinding] = []
    for page in pages:
        if not isinstance(page, dict):
            continue
        page_name = str(page.get("name") or page.get("slug") or "page")
        page_slug = str(page.get("slug") or page_name)
        root_elements = page_root_elements(page)

        def walk(elements: list[dict], *, guarded: bool) -> None:
            for element in elements:
                if not isinstance(element, dict):
                    continue
                has_guard = isinstance(element.get("visibility"), dict)
                if _warns_for_missing_guard(element, guarded=guarded, has_guard=has_guard):
                    location = _element_location(page_name, page_slug, element)
                    component = str(element.get("type") or "component")
                    findings.append(
                        LayoutFinding(
                            code="visibility.missing_empty_state_guard",
                            message=(
                                f'{component.capitalize()} on page "{page_name}" may render empty-state copy '
                                "without a visible guard."
                            ),
                            fix="Add `visible when state.<path> > 0` or set `empty_state: hidden`.",
                            location=location,
                        )
                    )
                children = element.get("children")
                if isinstance(children, list):
                    walk(children, guarded=guarded or has_guard)

        walk(root_elements, guarded=False)
    return findings


def _page_counts(elements: list[dict]) -> tuple[int, int]:
    filtered = [element for element in elements if not is_overlay_type(element.get("type"))]
    element_count = len(filtered)
    leaf_count = sum(1 for element in filtered if not is_container_type(element.get("type")))
    return element_count, leaf_count


def _page_path(page_slug: str) -> str:
    return f"page.{page_slug}"


def _story_icon_sort_key(finding: object) -> tuple[str, str, int, int, str]:
    code = getattr(finding, "code", "")
    location = getattr(finding, "location", None)
    path = getattr(location, "path", None) if location else None
    line = getattr(location, "line", None) if location else None
    column = getattr(location, "column", None) if location else None
    message = getattr(finding, "message", "")
    return (
        code,
        path or "",
        line or 0,
        column or 0,
        message,
    )


def _element_location(page_name: str, page_slug: str, element: dict) -> LayoutLocation:
    return LayoutLocation(
        page=page_name,
        page_slug=page_slug,
        path=element.get("element_id"),
        line=element.get("line"),
        column=element.get("column"),
    )


def _count_actions(element: dict) -> int:
    count = 0
    children = element.get("children")
    if isinstance(children, list):
        count += sum(1 for child in children if is_action_element(child.get("type")))
    actions = element.get("actions")
    if isinstance(actions, list):
        count += len(actions)
    return count


def _count_columns(element: dict) -> int:
    children = element.get("children")
    if not isinstance(children, list):
        return 0
    return sum(1 for child in children if child.get("type") == "column")


def _table_columns_signature(element: dict) -> tuple[tuple[str, str | None], ...] | None:
    columns = element.get("columns")
    if not isinstance(columns, list):
        return None
    signature: list[tuple[str, str | None]] = []
    for entry in columns:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name")
        if not isinstance(name, str) or not name:
            continue
        label = entry.get("label")
        signature.append((name, label if isinstance(label, str) else None))
    return tuple(signature) if signature else None


def _record_representation_findings(
    record_representations: dict[str, dict[str, list[LayoutLocation]]],
) -> Iterable[LayoutFinding]:
    findings: list[LayoutFinding] = []
    for record_name in sorted(record_representations):
        representations = record_representations[record_name]
        if len(representations) <= 1:
            continue
        ordered = sorted(representations)
        location = _pick_location([loc for items in representations.values() for loc in items])
        findings.append(
            rule_mixed_record_representation(
                record_name=record_name,
                representations=ordered,
                location=location,
            )
        )
    return findings


def _record_column_findings(
    record_columns: dict[str, dict[tuple[tuple[str, str | None], ...], list[LayoutLocation]]],
) -> Iterable[LayoutFinding]:
    findings: list[LayoutFinding] = []
    for record_name in sorted(record_columns):
        configs = record_columns[record_name]
        if len(configs) <= 1:
            continue
        location = _pick_location([loc for items in configs.values() for loc in items])
        findings.append(
            rule_inconsistent_columns(
                record_name=record_name,
                config_count=len(configs),
                location=location,
            )
        )
    return findings


def _pick_location(locations: list[LayoutLocation]) -> LayoutLocation:
    if not locations:
        return LayoutLocation(page="page", page_slug="page", path=None, line=None, column=None)
    return sorted(locations, key=lambda entry: entry.sort_key())[0]


def _warns_for_missing_guard(element: dict, *, guarded: bool, has_guard: bool) -> bool:
    if guarded or has_guard:
        return False
    element_type = element.get("type")
    if element_type not in {"list", "table"}:
        return False
    empty_state = element.get("empty_state")
    if isinstance(empty_state, dict):
        state_value = empty_state.get("state")
        if isinstance(state_value, str) and state_value.strip().lower() == "hidden":
            return False
    return True


__all__ = [
    "append_consistency_warnings",
    "append_copy_warnings",
    "append_icon_warnings",
    "append_layout_warnings",
    "append_visibility_warnings",
    "append_story_icon_warnings",
    "append_story_tone_warnings",
    "collect_layout_findings",
    "collect_visibility_findings",
]
