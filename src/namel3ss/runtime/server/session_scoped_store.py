from __future__ import annotations

import re
from copy import deepcopy

from namel3ss.runtime.storage.base import RecordScope
from namel3ss.schema.records import RecordSchema


_INTERNAL_RECORD_PREFIX = "__n3_"
_SESSION_RECORD_PREFIX = "__n3svc_session_"


class SessionScopedStore:
    """Storage adapter that isolates non-shared records and state per runtime session."""

    def __init__(self, base_store, session_id: str) -> None:
        self._base_store = base_store
        self._session_id = str(session_id)
        self._state: dict = {}
        self._schema_cache: dict[str, RecordSchema] = {}
        self._state_checkpoint: dict | None = None

    def begin(self) -> None:
        self._state_checkpoint = deepcopy(self._state)
        self._base_store.begin()

    def commit(self) -> None:
        self._state_checkpoint = None
        self._base_store.commit()

    def rollback(self) -> None:
        if self._state_checkpoint is not None:
            self._state = deepcopy(self._state_checkpoint)
            self._state_checkpoint = None
        self._base_store.rollback()

    def save(self, schema: RecordSchema, record: dict) -> dict:
        return self._base_store.save(self._scoped_schema(schema), record)

    def update(self, schema: RecordSchema, record: dict) -> dict:
        return self._base_store.update(self._scoped_schema(schema), record)

    def delete(self, schema: RecordSchema, record_id: object) -> bool:
        return self._base_store.delete(self._scoped_schema(schema), record_id)

    def find(self, schema: RecordSchema, predicate, scope: RecordScope | None = None) -> list[dict]:
        return self._base_store.find(self._scoped_schema(schema), predicate, scope=scope)

    def list_records(self, schema: RecordSchema, limit: int = 20, scope: RecordScope | None = None) -> list[dict]:
        return self._base_store.list_records(self._scoped_schema(schema), limit=limit, scope=scope)

    def check_unique(self, schema: RecordSchema, record: dict, scope: RecordScope | None = None) -> str | None:
        return self._base_store.check_unique(self._scoped_schema(schema), record, scope=scope)

    def clear(self) -> None:
        self._state.clear()

    def load_state(self) -> dict:
        return deepcopy(self._state)

    def save_state(self, state: dict) -> None:
        self._state = deepcopy(state or {})

    def get_metadata(self):
        return self._base_store.get_metadata()

    def _scoped_schema(self, schema: RecordSchema) -> RecordSchema:
        if _is_shared_schema(schema):
            return schema
        cache_key = schema.name
        cached = self._schema_cache.get(cache_key)
        if cached is not None:
            return cached
        scoped = RecordSchema(
            name=_scoped_record_name(schema.name, self._session_id),
            fields=list(schema.fields),
            shared=False,
            tenant_key=schema.tenant_key,
            ttl_hours=schema.ttl_hours,
        )
        self._schema_cache[cache_key] = scoped
        return scoped



def _is_shared_schema(schema: RecordSchema) -> bool:
    if bool(getattr(schema, "shared", False)):
        return True
    name = str(getattr(schema, "name", "") or "")
    return name.startswith(_INTERNAL_RECORD_PREFIX)



def _scoped_record_name(name: str, session_id: str) -> str:
    sanitized = _sanitize_session_id(session_id)
    return f"{_SESSION_RECORD_PREFIX}{sanitized}__{name}"



def _sanitize_session_id(session_id: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9_]", "_", str(session_id or ""))
    value = value.strip("_")
    return value or "anon"


__all__ = ["SessionScopedStore"]
