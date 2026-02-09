from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from namel3ss.runtime.contracts.runtime_schema import runtime_contract_schema_catalog


ACK_ENV = "BREAKING_CHANGE_ACK"
BASELINE_PATH = Path("resources/runtime_contract_schema_v1.json")
FIELD_KEYS = ("type", "required", "ref", "item_type", "item_ref")


def load_catalog(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _schema_map(payload: dict[str, object]) -> dict[str, dict[str, object]]:
    schemas = payload.get("schemas")
    if not isinstance(schemas, dict):
        return {}
    out: dict[str, dict[str, object]] = {}
    for key, value in schemas.items():
        if isinstance(key, str) and isinstance(value, dict):
            out[key] = value
    return out


def _field_map(schema: dict[str, object]) -> dict[str, dict[str, object]]:
    fields = schema.get("fields")
    if not isinstance(fields, list):
        return {}
    out: dict[str, dict[str, object]] = {}
    for item in fields:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        if isinstance(name, str) and name:
            out[name] = item
    return out


def check_contract_compatibility(baseline: dict[str, object], current: dict[str, object]) -> list[str]:
    issues: list[str] = []
    for key in ("contract_version", "schema_version"):
        if baseline.get(key) != current.get(key):
            issues.append(f"Top-level field changed: {key}")
    baseline_schemas = _schema_map(baseline)
    current_schemas = _schema_map(current)
    for schema_name in sorted(baseline_schemas):
        if schema_name not in current_schemas:
            issues.append(f"Schema removed: {schema_name}")
            continue
        baseline_schema = baseline_schemas[schema_name]
        current_schema = current_schemas[schema_name]
        if baseline_schema.get("additional_fields") != current_schema.get("additional_fields"):
            issues.append(f"Schema additional_fields changed: {schema_name}")
        baseline_fields = _field_map(baseline_schema)
        current_fields = _field_map(current_schema)
        for field_name in sorted(baseline_fields):
            if field_name not in current_fields:
                issues.append(f"Field removed: {schema_name}.{field_name}")
                continue
            baseline_field = baseline_fields[field_name]
            current_field = current_fields[field_name]
            for key in FIELD_KEYS:
                if baseline_field.get(key) != current_field.get(key):
                    issues.append(
                        f"Field shape changed: {schema_name}.{field_name}.{key} "
                        f"{baseline_field.get(key)!r} -> {current_field.get(key)!r}"
                    )
    return issues


def _ack_enabled() -> bool:
    value = str(os.environ.get(ACK_ENV, "")).strip().lower()
    return value in {"1", "true", "yes"}


def main() -> int:
    if not BASELINE_PATH.exists():
        raise SystemExit(f"Missing baseline schema snapshot: {BASELINE_PATH}")
    baseline = load_catalog(BASELINE_PATH)
    current = runtime_contract_schema_catalog()
    issues = check_contract_compatibility(baseline, current)
    if not issues:
        print("Contract compatibility check passed.")
        return 0
    print("Contract compatibility check found breaking changes:")
    for issue in issues:
        print(f"- {issue}")
    if _ack_enabled():
        print(f"{ACK_ENV}=1 set; allowing acknowledged breaking changes.")
        return 0
    print(f"Set {ACK_ENV}=1 to acknowledge intentional breakage.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
