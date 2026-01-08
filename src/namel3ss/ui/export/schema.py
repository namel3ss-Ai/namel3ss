from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.ui.fields import field_to_ui


SCHEMA_EXPORT_VERSION = "1"


def collect_ui_record_names(manifest: dict) -> list[str]:
    records: set[str] = set()
    pages = manifest.get("pages") if isinstance(manifest, dict) else None
    for page in pages or []:
        elements = page.get("elements") if isinstance(page, dict) else None
        for element in _walk_elements(elements or []):
            record = _record_name_for_element(element)
            if record:
                records.add(record)
    return sorted(records)


def build_schema_export(program, manifest: dict) -> dict:
    record_names = collect_ui_record_names(manifest)
    record_map = {rec.name: rec for rec in getattr(program, "records", [])}
    items: list[dict] = []
    for name in record_names:
        record = record_map.get(name)
        if record is None:
            raise Namel3ssError(f"UI export references unknown record '{name}'.")
        fields = [field_to_ui(field) for field in record.fields]
        items.append({"name": record.name, "fields": fields})
    return {
        "schema_version": SCHEMA_EXPORT_VERSION,
        "records": items,
    }


def _record_name_for_element(element: dict) -> str | None:
    element_type = element.get("type")
    if element_type in {"form", "table", "list", "chart"}:
        record = element.get("record")
        return record if isinstance(record, str) else None
    return None


def _walk_elements(elements: list[dict]) -> list[dict]:
    collected: list[dict] = []
    for element in elements:
        collected.append(element)
        children = element.get("children")
        if isinstance(children, list) and children:
            collected.extend(_walk_elements(children))
    return collected


__all__ = ["SCHEMA_EXPORT_VERSION", "build_schema_export", "collect_ui_record_names"]
