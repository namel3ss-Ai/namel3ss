from __future__ import annotations

from decimal import Decimal
from typing import Dict, List, Callable, Optional, Any

from namel3ss.errors.base import Namel3ssError
from namel3ss.schema.records import EXPIRES_AT_FIELD, SYSTEM_FIELDS, TENANT_KEY_FIELD, RecordSchema
from namel3ss.runtime.storage.predicate import PredicatePlan
from namel3ss.runtime.storage.metadata import PersistenceMetadata
from namel3ss.runtime.storage.base import RecordScope
from namel3ss.utils.numbers import is_number, to_decimal


class MemoryStore:
    def __init__(self) -> None:
        self._data: Dict[str, List[dict]] = {}
        self._unique_indexes: Dict[str, Dict[str, Dict[object, dict]]] = {}
        self._counters: Dict[str, int] = {}
        self._state: dict = {}
        self._checkpoint: Optional[tuple[Dict[str, List[dict]], Dict[str, Dict[str, Dict[object, dict]]], Dict[str, int], dict]] = None

    def begin(self) -> None:
        self._checkpoint = (
            {k: [dict(rec) for rec in v] for k, v in self._data.items()},
            {k: {fk: dict(vals) for fk, vals in v.items()} for k, v in self._unique_indexes.items()},
            dict(self._counters),
            dict(self._state),
        )

    def commit(self) -> None:
        self._checkpoint = None

    def rollback(self) -> None:
        if self._checkpoint is None:
            return
        self._data, self._unique_indexes, self._counters, self._state = self._checkpoint
        self._checkpoint = None

    def save(self, schema: RecordSchema, record: dict) -> dict:
        rec_name = schema.name
        if rec_name not in self._data:
            self._data[rec_name] = []
            self._unique_indexes[rec_name] = {}
            self._counters[rec_name] = 1

        # Handle auto id
        if "id" in schema.field_map:
            record.setdefault("id", self._counters[rec_name])
        else:
            record.setdefault("_id", self._counters[rec_name])
        self._counters[rec_name] += 1

        conflict_field = self.check_unique(schema, record)
        if conflict_field:
            raise Namel3ssError(f"Record '{rec_name}' violates unique constraint on '{conflict_field}'")
        for field in schema.unique_fields:
            value = record.get(field)
            if value is None:
                continue
            idx = self._unique_indexes[rec_name].setdefault(field, {})
            idx[_unique_key(schema, record, value)] = record

        self._data[rec_name].append(record)
        return _strip_system_fields(record)

    def update(self, schema: RecordSchema, record: dict) -> dict:
        rec_name = schema.name
        records = self._data.get(rec_name, [])
        id_col = "id" if "id" in schema.field_map else "_id"
        record_id = record.get(id_col)
        if record_id is None:
            raise Namel3ssError(f"Record '{rec_name}' update requires {id_col}")
        existing = None
        for stored in records:
            if stored.get(id_col) == record_id:
                existing = stored
                break
        if existing is None:
            raise Namel3ssError(f"Record '{rec_name}' with {id_col}={record_id} was not found")

        updated = dict(existing)
        for field in schema.fields:
            if field.name in record:
                updated[field.name] = record.get(field.name)

        indexes = self._unique_indexes.setdefault(rec_name, {})
        for field in schema.unique_fields:
            idx = indexes.setdefault(field, {})
            old_value = existing.get(field)
            new_value = updated.get(field)
            old_key = _unique_key(schema, existing, old_value) if old_value is not None else None
            new_key = _unique_key(schema, existing, new_value) if new_value is not None else None
            if new_key is not None and new_key in idx and idx[new_key] is not existing:
                raise Namel3ssError(f"Record '{rec_name}' violates unique constraint on '{field}'")
            if old_key is not None and old_key != new_key:
                idx.pop(old_key, None)
            if new_key is not None:
                idx[new_key] = existing

        existing.update(updated)
        return _strip_system_fields(existing)

    def delete(self, schema: RecordSchema, record_id: object) -> bool:
        rec_name = schema.name
        records = self._data.get(rec_name, [])
        id_col = "id" if "id" in schema.field_map else "_id"
        for idx, stored in enumerate(list(records)):
            if stored.get(id_col) != record_id:
                continue
            records.pop(idx)
            for field in schema.unique_fields:
                value = stored.get(field)
                if value is None:
                    continue
                key = _unique_key(schema, stored, value)
                self._unique_indexes.get(rec_name, {}).get(field, {}).pop(key, None)
            return True
        return False

    def find(
        self,
        schema: RecordSchema,
        predicate: Callable[[dict], bool] | dict[str, Any],
        scope: RecordScope | None = None,
    ) -> List[dict]:
        scope = scope or RecordScope()
        self._cleanup_expired(schema, scope)
        if isinstance(predicate, PredicatePlan):
            predicate = predicate.predicate
        records = self._data.get(schema.name, [])
        if isinstance(predicate, dict):
            return [
                _strip_system_fields(rec)
                for rec in records
                if _record_visible(schema, rec, scope) and _matches_filter(rec, predicate)
            ]
        results = []
        for rec in records:
            if not _record_visible(schema, rec, scope):
                continue
            clean = _strip_system_fields(rec)
            if predicate(clean):
                results.append(clean)
        return results

    def check_unique(self, schema: RecordSchema, record: dict, scope: RecordScope | None = None) -> str | None:
        scope = scope or RecordScope()
        self._cleanup_expired(schema, scope)
        rec_name = schema.name
        indexes = self._unique_indexes.setdefault(rec_name, {})
        for field in schema.unique_fields:
            value = record.get(field)
            if value is None:
                continue
            idx = indexes.setdefault(field, {})
            key = _unique_key(schema, record, value)
            if key in idx:
                return field
        return None

    def list_records(self, schema: RecordSchema, limit: int = 20, scope: RecordScope | None = None) -> List[dict]:
        scope = scope or RecordScope()
        self._cleanup_expired(schema, scope)
        records = list(self._data.get(schema.name, []))
        key_order = "id" if "id" in schema.field_map else "_id"
        records.sort(key=lambda rec: rec.get(key_order, 0))
        visible = [
            _strip_system_fields(rec) for rec in records if _record_visible(schema, rec, scope)
        ]
        return visible[:limit]

    def _cleanup_expired(self, schema: RecordSchema, scope: RecordScope) -> None:
        if schema.ttl_hours is None or scope.now is None:
            return
        rec_name = schema.name
        if rec_name not in self._data:
            return
        records = self._data[rec_name]
        remaining = [rec for rec in records if not _is_expired(schema, rec, scope.now)]
        if len(remaining) == len(records):
            return
        self._data[rec_name] = remaining
        self._unique_indexes[rec_name] = _rebuild_indexes(schema, remaining)

    def clear(self) -> None:
        self._data.clear()
        self._unique_indexes.clear()
        self._counters.clear()
        self._state.clear()

    def load_state(self) -> dict:
        return dict(self._state)

    def save_state(self, state: dict) -> None:
        self._state = dict(state)

    def get_metadata(self) -> PersistenceMetadata:
        return PersistenceMetadata(
            enabled=False,
            kind="memory",
            path=None,
            schema_version=None,
        )


def _matches_filter(record: dict, filters: dict[str, Any]) -> bool:
    for field, expected in filters.items():
        value = record.get(field)
        if isinstance(expected, Contains):
            target = "" if value is None else str(value)
            if expected.value not in target:
                return False
            continue
        if value != expected:
            return False
    return True


class Contains:
    def __init__(self, value: Any) -> None:
        self.value = "" if value is None else str(value)


def _strip_system_fields(record: dict) -> dict:
    return {key: value for key, value in record.items() if key not in SYSTEM_FIELDS}


def _unique_key(schema: RecordSchema, record: dict, value: object) -> object:
    if schema.tenant_key:
        return (record.get(TENANT_KEY_FIELD), value)
    return value


def _record_visible(schema: RecordSchema, record: dict, scope: RecordScope) -> bool:
    if schema.tenant_key and scope.tenant_value is not None:
        if record.get(TENANT_KEY_FIELD) != scope.tenant_value:
            return False
    if _is_expired(schema, record, scope.now):
        return False
    return True


def _is_expired(schema: RecordSchema, record: dict, now: Decimal | None) -> bool:
    if schema.ttl_hours is None:
        return False
    if now is None:
        return False
    expires_at = record.get(EXPIRES_AT_FIELD)
    if expires_at is None:
        return True
    if is_number(expires_at):
        return to_decimal(expires_at) <= now
    return True


def _rebuild_indexes(schema: RecordSchema, records: list[dict]) -> dict[str, Dict[object, dict]]:
    rebuilt: dict[str, Dict[object, dict]] = {}
    for field in schema.unique_fields:
        rebuilt[field] = {}
    for record in records:
        for field in schema.unique_fields:
            value = record.get(field)
            if value is None:
                continue
            rebuilt[field][_unique_key(schema, record, value)] = record
    return rebuilt
