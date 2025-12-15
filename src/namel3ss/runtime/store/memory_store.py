from __future__ import annotations

from typing import Dict, List, Callable

from namel3ss.errors.base import Namel3ssError
from namel3ss.schema.records import RecordSchema


class MemoryStore:
    def __init__(self) -> None:
        self._data: Dict[str, List[dict]] = {}
        self._unique_indexes: Dict[str, Dict[str, Dict[object, dict]]] = {}
        self._counters: Dict[str, int] = {}

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

    def find(self, schema: RecordSchema, predicate: Callable[[dict], bool]) -> List[dict]:
        records = self._data.get(schema.name, [])
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
