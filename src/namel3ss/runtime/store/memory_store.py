from __future__ import annotations

from typing import Dict, List, Callable, Optional, Any

from namel3ss.errors.base import Namel3ssError
from namel3ss.schema.records import RecordSchema
from namel3ss.runtime.storage.metadata import PersistenceMetadata


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
            idx[value] = record

        self._data[rec_name].append(record)
        return record

    def find(self, schema: RecordSchema, predicate: Callable[[dict], bool] | dict[str, Any]) -> List[dict]:
        records = self._data.get(schema.name, [])
        if isinstance(predicate, dict):
            return [rec for rec in records if _matches_filter(rec, predicate)]
        return [rec for rec in records if predicate(rec)]

    def check_unique(self, schema: RecordSchema, record: dict) -> str | None:
        rec_name = schema.name
        indexes = self._unique_indexes.setdefault(rec_name, {})
        for field in schema.unique_fields:
            value = record.get(field)
            if value is None:
                continue
            idx = indexes.setdefault(field, {})
            if value in idx:
                return field
        return None

    def list_records(self, schema: RecordSchema, limit: int = 20) -> List[dict]:
        records = list(self._data.get(schema.name, []))
        key_order = "id" if "id" in schema.field_map else "_id"
        records.sort(key=lambda rec: rec.get(key_order, 0))
        return records[:limit]

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
