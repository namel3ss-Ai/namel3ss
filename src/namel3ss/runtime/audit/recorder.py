from __future__ import annotations

import copy
import os
import re
import time
from decimal import Decimal
from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.storage.base import Storage
from namel3ss.schema.records import EXPIRES_AT_FIELD
from namel3ss.secrets import redact_payload as redact_secrets, collect_secret_values
from namel3ss.observe import record_event
from namel3ss.schema.records import FieldSchema, RecordSchema


AUDIT_RECORD_NAME = "__n3_audit_log"

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
    ttl_hours = _audit_ttl_hours()
    return RecordSchema(
        name=AUDIT_RECORD_NAME,
        fields=[
            FieldSchema(name="flow", type_name="text"),
            FieldSchema(name="action", type_name="text"),
            FieldSchema(name="actor", type_name="json"),
            FieldSchema(name="timestamp", type_name="number"),
            FieldSchema(name="record_ids", type_name="json"),
            FieldSchema(name="before", type_name="json"),
            FieldSchema(name="after", type_name="json"),
            FieldSchema(name="proof_id", type_name="text"),
            FieldSchema(name="build_id", type_name="text"),
        ],
        ttl_hours=ttl_hours,
    )


def record_audit_entry(
    store: Storage,
    *,
    flow_name: str,
    action_name: str | None = None,
    identity: dict | None,
    before: dict,
    after: dict,
    record_changes: list[dict] | None = None,
    project_root: str | None = None,
    secret_values: list[str] | None = None,
) -> None:
    schema = audit_schema()
    secrets = secret_values or collect_secret_values()
    proof_meta = _load_active_proof(project_root)
    entry = {
        "flow": flow_name,
        "action": action_name,
        "actor": _actor_summary(identity),
        "timestamp": _now_decimal(),
        "record_ids": _record_ids(record_changes),
        "before": redact_secrets(redact_payload(copy.deepcopy(before)), secrets),
        "after": redact_secrets(redact_payload(copy.deepcopy(after)), secrets),
        "proof_id": proof_meta.get("proof_id"),
        "build_id": proof_meta.get("build_id"),
    }
    if schema.ttl_hours is not None:
        entry[EXPIRES_AT_FIELD] = _compute_expires_at(schema.ttl_hours)
    try:
        saved = store.save(schema, entry)
    except Exception as exc:
        raise Namel3ssError(_audit_failed_message(flow_name)) from exc
    if project_root:
        record_event(
            Path(project_root),
            {
                "type": "audit",
                "audit_id": saved.get("id") if isinstance(saved, dict) else None,
                "flow": flow_name,
                "action": action_name,
                "actor": entry.get("actor"),
                "record_ids": entry.get("record_ids"),
                "time": float(entry.get("timestamp", time.time())),
            },
            secret_values=secrets,
        )


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


def _audit_ttl_hours() -> Decimal | None:
    raw = os.getenv("N3_AUDIT_RETENTION_DAYS", "").strip()
    if not raw:
        days = 30
    else:
        try:
            days = int(raw)
        except ValueError:
            days = 30
    if days <= 0:
        return None
    return Decimal(str(days * 24))


def _compute_expires_at(ttl_hours: Decimal) -> Decimal:
    return _now_decimal() + (ttl_hours * Decimal("3600"))


def _record_ids(record_changes: list[dict] | None) -> list[dict]:
    if not record_changes:
        return []
    seen = set()
    unique: list[dict] = []
    for entry in record_changes:
        if not isinstance(entry, dict):
            continue
        key = (entry.get("record"), entry.get("id"))
        if key in seen:
            continue
        seen.add(key)
        unique.append({"record": entry.get("record"), "id": entry.get("id")})
    return unique


def _load_active_proof(project_root: str | None) -> dict:
    if not project_root:
        return {}
    path = Path(project_root) / ".namel3ss" / "active_proof.json"
    if not path.exists():
        return {}
    try:
        import json

        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}
