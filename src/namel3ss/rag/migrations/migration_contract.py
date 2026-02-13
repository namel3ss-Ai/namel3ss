from __future__ import annotations

from namel3ss.rag.contracts.value_norms import (
    int_value,
    map_value,
    merge_extensions,
    text_value,
    unknown_extensions,
)
from namel3ss.rag.determinism.json_policy import (
    canonical_contract_copy,
    canonical_contract_hash,
)


MIGRATION_STEP_SCHEMA_VERSION = "rag.migration_step@1"
MIGRATION_MANIFEST_SCHEMA_VERSION = "rag.migration_manifest@1"


def build_migration_step(
    *,
    step_id: str = "",
    step_index: int = 0,
    operation: str,
    target_path: str,
    value: object = None,
    from_path: str = "",
    on_missing: str = "skip",
    schema_version: str = MIGRATION_STEP_SCHEMA_VERSION,
    extensions: dict[str, object] | None = None,
) -> dict[str, object]:
    operation_value = _operation_value(operation)
    target_value = _path_value(target_path)
    from_value = _path_value(from_path)
    value_copy = canonical_contract_copy(value)
    step_id_value = text_value(step_id) or _build_step_id(
        operation=operation_value,
        target_path=target_value,
        from_path=from_value,
        value=value_copy,
        step_index=step_index,
    )
    return {
        "schema_version": text_value(schema_version, default=MIGRATION_STEP_SCHEMA_VERSION) or MIGRATION_STEP_SCHEMA_VERSION,
        "step_id": step_id_value,
        "step_index": int_value(step_index, default=0, minimum=0),
        "operation": operation_value,
        "target_path": target_value,
        "from_path": from_value,
        "on_missing": _on_missing_value(on_missing),
        "value": value_copy,
        "extensions": merge_extensions(extensions),
    }


def normalize_migration_step(value: object, *, step_index: int = 0) -> dict[str, object]:
    data = map_value(value)
    extensions = merge_extensions(
        map_value(data.get("extensions")),
        unknown_extensions(data, known_keys=_STEP_FIELDS),
    )
    return build_migration_step(
        step_id=text_value(data.get("step_id")),
        step_index=step_index,
        operation=text_value(data.get("operation"), default="set_value") or "set_value",
        target_path=text_value(data.get("target_path")),
        value=data.get("value"),
        from_path=text_value(data.get("from_path")),
        on_missing=text_value(data.get("on_missing"), default="skip") or "skip",
        schema_version=text_value(data.get("schema_version"), default=MIGRATION_STEP_SCHEMA_VERSION)
        or MIGRATION_STEP_SCHEMA_VERSION,
        extensions=extensions,
    )


def build_migration_manifest(
    *,
    name: str,
    steps: object,
    manifest_id: str | None = None,
    schema_version: str = MIGRATION_MANIFEST_SCHEMA_VERSION,
    extensions: dict[str, object] | None = None,
) -> dict[str, object]:
    name_value = text_value(name)
    step_rows = _normalize_step_rows(steps)
    manifest_id_value = text_value(manifest_id) or _build_manifest_id(name=name_value, steps=step_rows)
    return {
        "schema_version": text_value(schema_version, default=MIGRATION_MANIFEST_SCHEMA_VERSION)
        or MIGRATION_MANIFEST_SCHEMA_VERSION,
        "manifest_id": manifest_id_value,
        "name": name_value,
        "steps": step_rows,
        "extensions": merge_extensions(extensions),
    }


def normalize_migration_manifest(value: object) -> dict[str, object]:
    data = map_value(value)
    name_value = text_value(data.get("name"))
    step_rows = _normalize_step_rows(data.get("steps"))
    manifest_id_value = text_value(data.get("manifest_id")) or _build_manifest_id(name=name_value, steps=step_rows)
    extensions = merge_extensions(
        map_value(data.get("extensions")),
        unknown_extensions(data, known_keys=_MANIFEST_FIELDS),
    )
    return {
        "schema_version": text_value(data.get("schema_version"), default=MIGRATION_MANIFEST_SCHEMA_VERSION)
        or MIGRATION_MANIFEST_SCHEMA_VERSION,
        "manifest_id": manifest_id_value,
        "name": name_value,
        "steps": step_rows,
        "extensions": extensions,
    }


def _normalize_step_rows(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    rows: list[dict[str, object]] = []
    for index, item in enumerate(value):
        rows.append(normalize_migration_step(item, step_index=index))
    rows.sort(key=lambda row: (int(row.get("step_index") or 0), text_value(row.get("step_id"))))
    return rows


def _build_step_id(
    *,
    operation: str,
    target_path: str,
    from_path: str,
    value: object,
    step_index: int,
) -> str:
    payload = {
        "from_path": from_path,
        "operation": operation,
        "step_index": int_value(step_index, default=0, minimum=0),
        "target_path": target_path,
        "value": canonical_contract_copy(value),
    }
    digest = canonical_contract_hash(payload)
    return f"migstep_{digest[:20]}"


def _build_manifest_id(*, name: str, steps: list[dict[str, object]]) -> str:
    payload = {
        "name": name,
        "steps": [canonical_contract_copy(step) for step in steps],
    }
    digest = canonical_contract_hash(payload)
    return f"mig_{digest[:20]}"


def _operation_value(value: object) -> str:
    token = text_value(value, default="set_value") or "set_value"
    if token not in {"set_value", "remove_value", "rename_value"}:
        return "set_value"
    return token


def _on_missing_value(value: object) -> str:
    token = text_value(value, default="skip") or "skip"
    if token not in {"skip", "error"}:
        return "skip"
    return token


def _path_value(value: object) -> str:
    token = text_value(value)
    parts = [part.strip() for part in token.split(".") if part.strip()]
    return ".".join(parts)


_STEP_FIELDS = {
    "schema_version",
    "step_id",
    "step_index",
    "operation",
    "target_path",
    "from_path",
    "on_missing",
    "value",
    "extensions",
}

_MANIFEST_FIELDS = {
    "schema_version",
    "manifest_id",
    "name",
    "steps",
    "extensions",
}


__all__ = [
    "MIGRATION_MANIFEST_SCHEMA_VERSION",
    "MIGRATION_STEP_SCHEMA_VERSION",
    "build_migration_manifest",
    "build_migration_step",
    "normalize_migration_manifest",
    "normalize_migration_step",
]
