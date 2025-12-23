from __future__ import annotations

import copy
import re
import time
from decimal import Decimal

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.storage.base import Storage
from namel3ss.schema.records import FieldSchema, RecordSchema


AUDIT_RECORD_NAME = "__n3_audit_log"

_AUDIT_SCHEMA = RecordSchema(
    name=AUDIT_RECORD_NAME,
    fields=[
        FieldSchema(name="flow", type_name="text"),
        FieldSchema(name="actor", type_name="json"),
        FieldSchema(name="timestamp", type_name="number"),
        FieldSchema(name="before", type_name="json"),
        FieldSchema(name="after", type_name="json"),
    ],
)

_REDACT_PATTERN = re.compile(
    r"(password|passwd|secret|token|api[_-]?key|access[_-]?key|auth|credential)",
    re.IGNORECASE,
)
_ACTOR_FIELDS = {
    "id",
    "user_id",
    "email",
    "name",
    "role",
    "trust_level",
    "organization_id",
    "org_id",
    "tenant_id",
    "tenant",
}


def audit_schema() -> RecordSchema:
    return _AUDIT_SCHEMA


def record_audit_entry(
    store: Storage,
    *,
    flow_name: str,
    identity: dict | None,
    before: dict,
    after: dict,
) -> None:
    entry = {
        "flow": flow_name,
        "actor": _actor_summary(identity),
        "timestamp": _now_decimal(),
        "before": redact_payload(copy.deepcopy(before)),
        "after": redact_payload(copy.deepcopy(after)),
    }
    try:
        store.save(_AUDIT_SCHEMA, entry)
    except Exception as exc:
        raise Namel3ssError(_audit_failed_message(flow_name)) from exc


def redact_payload(value: object) -> object:
    if isinstance(value, dict):
        redacted: dict[str, object] = {}
        for key, val in value.items():
            if _REDACT_PATTERN.search(str(key)):
                redacted[key] = "***"
            else:
                redacted[key] = redact_payload(val)
        return redacted
    if isinstance(value, list):
        return [redact_payload(item) for item in value]
    if isinstance(value, (str, int, float, bool, Decimal)) or value is None:
        return value
    return str(value)


def _actor_summary(identity: dict | None) -> dict:
    if not identity:
        return {}
    return {key: identity[key] for key in _ACTOR_FIELDS if key in identity}


def _audit_failed_message(flow_name: str) -> str:
    return build_guidance_message(
        what="Audit entry could not be recorded.",
        why=f'The audited flow "{flow_name}" could not write to the audit log.',
        fix="Check persistence health or disable auditing for the flow.",
        example='flow "update_order": audited',
    )


def _now_decimal() -> Decimal:
    return Decimal(str(time.time()))
