from __future__ import annotations

import hashlib
from decimal import Decimal
from dataclasses import dataclass

from namel3ss.runtime.auth.identity_model import normalize_identity
from namel3ss.runtime.storage.base import Storage
from namel3ss.schema.records import FieldConstraint, FieldSchema, RecordSchema


SESSION_TABLE = "__n3_sessions"
META_TABLE = "__n3_auth_meta"
META_CLOCK = "auth_clock"
META_COUNTER = "session_counter"


@dataclass(frozen=True)
class SessionRecord:
    session_id: str
    status: str
    identity: dict
    created_tick: int | None
    expires_at: int | None


class SessionStore:
    def __init__(self, store: Storage) -> None:
        self.store = store

    def create_session(self, identity: dict, *, expires_in: int | None = None) -> SessionRecord:
        session_counter = self._next_meta(META_COUNTER, start=1)
        now_tick = self.tick()
        expires_at = None
        if isinstance(expires_in, int) and expires_in > 0:
            expires_at = now_tick + expires_in
        session_id = f"session_{session_counter}"
        record = {
            "session_id": session_id,
            "status": "active",
            "identity": normalize_identity(identity),
            "created_tick": int(now_tick),
            "expires_at": expires_at,
        }
        saved = self.store.save(_session_schema(), record)
        return SessionRecord(
            session_id=str(saved.get("session_id") or session_id),
            status=str(saved.get("status") or "active"),
            identity=dict(saved.get("identity") or {}),
            created_tick=_coerce_int(saved.get("created_tick")),
            expires_at=_coerce_int(saved.get("expires_at")),
        )

    def get_session(self, session_id: str, *, now_tick: int | None = None) -> SessionRecord | None:
        if not session_id:
            return None
        record = self._find_session_record(session_id)
        if record is None:
            return None
        status = str(record.get("status") or "active")
        created_tick = _coerce_int(record.get("created_tick"))
        expires_at = _coerce_int(record.get("expires_at"))
        now = now_tick if isinstance(now_tick, int) else self.current_tick()
        if expires_at is not None and isinstance(now, int) and now >= expires_at:
            status = "expired"
        return SessionRecord(
            session_id=str(record.get("session_id") or session_id),
            status=status,
            identity=dict(record.get("identity") or {}),
            created_tick=created_tick,
            expires_at=expires_at,
        )

    def revoke_session(self, session_id: str) -> bool:
        record = self._find_session_record(session_id)
        if record is None:
            return False
        updated = dict(record)
        updated["status"] = "revoked"
        self.store.update(_session_schema(), updated)
        return True

    def current_tick(self) -> int:
        return self._get_meta(META_CLOCK, default=0)

    def tick(self) -> int:
        return self._next_meta(META_CLOCK, start=1)

    def session_summary(self, session: SessionRecord | None) -> dict | None:
        if session is None:
            return None
        summary = {
            "id": redact_session_id(session.session_id),
            "status": session.status,
            "created_tick": session.created_tick,
            "expires_at": session.expires_at,
        }
        return summary

    def _find_session_record(self, session_id: str) -> dict | None:
        results = self.store.find(_session_schema(), {"session_id": session_id})
        if not results:
            return None
        record = results[0]
        if not isinstance(record, dict):
            return None
        return record

    def _get_meta(self, key: str, *, default: int) -> int:
        record = self._find_meta_record(key)
        if record is None:
            return default
        value = _coerce_int(record.get("value"))
        return value if value is not None else default

    def _next_meta(self, key: str, *, start: int) -> int:
        record = self._find_meta_record(key)
        if record is None:
            value = int(start)
            created = {"key": key, "value": value}
            self.store.save(_meta_schema(), created)
            return value
        value = _coerce_int(record.get("value"))
        next_value = (value if value is not None else start) + 1
        updated = dict(record)
        updated["value"] = int(next_value)
        self.store.update(_meta_schema(), updated)
        return int(next_value)

    def _find_meta_record(self, key: str) -> dict | None:
        results = self.store.find(_meta_schema(), {"key": key})
        if not results:
            return None
        record = results[0]
        if not isinstance(record, dict):
            return None
        return record


def redact_session_id(session_id: str) -> str:
    if not isinstance(session_id, str) or not session_id:
        return "session:missing"
    digest = hashlib.sha256(session_id.encode("utf-8")).hexdigest()
    return f"session:{digest[:12]}"


def _session_schema() -> RecordSchema:
    return RecordSchema(
        name=SESSION_TABLE,
        fields=[
            FieldSchema("session_id", "text", FieldConstraint(kind="unique")),
            FieldSchema("status", "text"),
            FieldSchema("identity", "json"),
            FieldSchema("created_tick", "number"),
            FieldSchema("expires_at", "number"),
        ],
    )


def _meta_schema() -> RecordSchema:
    return RecordSchema(
        name=META_TABLE,
        fields=[
            FieldSchema("key", "text", FieldConstraint(kind="unique")),
            FieldSchema("value", "number"),
        ],
    )


def _coerce_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, Decimal):
        return int(value)
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


__all__ = ["META_CLOCK", "META_COUNTER", "SessionRecord", "SessionStore", "redact_session_id"]
