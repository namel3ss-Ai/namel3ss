from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Dict, List, Any

from namel3ss.errors.base import Namel3ssError
from namel3ss.schema.records import RecordSchema
from namel3ss.runtime.storage.metadata import PersistenceMetadata
from namel3ss.runtime.store.memory_store import Contains


SCHEMA_VERSION = 2


def _slug(name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_]", "_", name).lower()
    return slug or "unnamed"


class SQLiteStore:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.conn = sqlite3.connect(self.db_path)
        except sqlite3.Error as err:
            raise Namel3ssError(f"Could not open SQLite store at {self.db_path}: {err}") from err
        self.conn.row_factory = sqlite3.Row
        self._prepared_tables: set[str] = set()
        self._prepared_indexes: Dict[str, set[str]] = {}
        self._apply_pragmas()
        self._ensure_schema_version()

    def begin(self) -> None:
        self.conn.execute("BEGIN")

    def commit(self) -> None:
        self.conn.commit()

    def rollback(self) -> None:
        self.conn.rollback()

    def clear(self) -> None:
        cursor = self.conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row["name"] for row in cursor.fetchall() if not row["name"].startswith("sqlite_")]
        for table in tables:
            self.conn.execute(f"DROP TABLE IF EXISTS {table}")
        self.conn.commit()
        self._prepared_tables.clear()
        self._prepared_indexes.clear()
        self._ensure_schema_version()

    def _apply_pragmas(self) -> None:
        try:
            self.conn.execute("PRAGMA journal_mode=WAL;")
            self.conn.execute("PRAGMA synchronous=NORMAL;")
            self.conn.execute("PRAGMA foreign_keys=ON;")
            self.conn.execute("PRAGMA busy_timeout=5000;")
        except Exception:
            pass

    def _ensure_schema_version(self) -> None:
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL);"
        )
        row = self.conn.execute("SELECT version FROM schema_version LIMIT 1").fetchone()
        if row is None:
            self.conn.execute("INSERT INTO schema_version (version) VALUES (?)", (SCHEMA_VERSION,))
            self.conn.commit()
        elif row["version"] < SCHEMA_VERSION:
            self._migrate(row["version"])
        elif row["version"] > SCHEMA_VERSION:
            raise Namel3ssError(
                f"Unsupported schema version {row['version']} in {self.db_path}. Expected {SCHEMA_VERSION}."
            )

        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS app_state (id INTEGER PRIMARY KEY CHECK (id = 1), payload TEXT NOT NULL)"
        )
        self.conn.commit()

    def _migrate(self, current_version: int) -> None:
        if current_version < 1 or current_version > SCHEMA_VERSION:
            raise Namel3ssError(
                f"Cannot migrate unknown schema version {current_version} in {self.db_path} (target {SCHEMA_VERSION})."
            )
        if current_version == 1:
            self._migrate_v1_to_v2()
        self.conn.execute("UPDATE schema_version SET version = ?", (SCHEMA_VERSION,))
        self.conn.commit()

    def _migrate_v1_to_v2(self) -> None:
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS app_state (id INTEGER PRIMARY KEY CHECK (id = 1), payload TEXT NOT NULL)"
        )

    def _ensure_table(self, schema: RecordSchema) -> None:
        table = _slug(schema.name)
        if table in self._prepared_tables:
            return
        id_col = "id" if "id" in schema.field_map else "_id"
        columns = [f"{id_col} INTEGER PRIMARY KEY AUTOINCREMENT"]
        for field in schema.fields:
            col_name = _slug(field.name)
            col_type = self._sql_type(field.type_name)
            if col_name == id_col:
                continue
            columns.append(f"{col_name} {col_type}")
        uniques = [f"UNIQUE({_slug(f)})" for f in schema.unique_fields]
        stmt = f"CREATE TABLE IF NOT EXISTS {table} ({', '.join(columns + uniques)})"
        self.conn.execute(stmt)
        self._prepared_tables.add(table)
        self._ensure_indexes(schema)
        self.conn.commit()

    def _ensure_indexes(self, schema: RecordSchema) -> None:
        table = _slug(schema.name)
        prepared = self._prepared_indexes.setdefault(table, set())
        if not prepared:
            prepared.update(self._existing_indexes(table))
        for field in schema.unique_fields:
            col = _slug(field)
            index_name = self._index_name(table, col)
            if index_name in prepared:
                continue
            self.conn.execute(f"CREATE UNIQUE INDEX IF NOT EXISTS {index_name} ON {table} ({col})")
            prepared.add(index_name)

    def _existing_indexes(self, table: str) -> set[str]:
        rows = self.conn.execute(f"PRAGMA index_list('{table}')").fetchall()
        return {row["name"] for row in rows}

    def _index_name(self, table: str, column: str) -> str:
        return f"idx_{table}_{column}_uniq"

    def _sql_type(self, type_name: str) -> str:
        name = type_name.lower()
        if name in {"string", "str", "text", "json"}:
            return "TEXT"
        if name in {"int", "integer"}:
            return "INTEGER"
        if name == "boolean" or name == "bool":
            return "INTEGER"
        if name == "number":
            return "REAL"
        return "TEXT"

    def _serialize_value(self, type_name: str, value):
        name = type_name.lower()
        if name in {"string", "str", "text"}:
            return value
        if name in {"int", "integer"}:
            return int(value) if value is not None else None
        if name == "number":
            return float(value) if value is not None else None
        if name in {"boolean", "bool"}:
            return 1 if value else 0 if value is not None else None
        if name == "json":
            return json.dumps(value) if value is not None else None
        return value

    def _deserialize_row(self, schema: RecordSchema, row: sqlite3.Row) -> dict:
        data: dict = {}
        for field in schema.fields:
            col = _slug(field.name)
            if col not in row.keys():
                continue
            val = row[col]
            if field.type_name.lower() in {"boolean", "bool"}:
                data[field.name] = bool(val)
            elif field.type_name.lower() == "json" and val is not None:
                try:
                    data[field.name] = json.loads(val)
                except Exception:
                    data[field.name] = val
            elif field.type_name.lower() == "int" or field.type_name.lower() == "integer":
                data[field.name] = int(val) if val is not None else None
            elif field.type_name.lower() == "number":
                data[field.name] = float(val) if val is not None else None
            else:
                data[field.name] = val
        id_col = "id" if "id" in schema.field_map else "_id"
        if id_col in row.keys():
            data[id_col] = row[id_col]
        return data

    def save(self, schema: RecordSchema, record: dict) -> dict:
        self._ensure_table(schema)
        id_col = "id" if "id" in schema.field_map else "_id"
        col_names = []
        values = []
        for field in schema.fields:
            if field.name == id_col:
                continue
            col_names.append(_slug(field.name))
            values.append(self._serialize_value(field.type_name, record.get(field.name)))
        columns_clause = ", ".join(col_names)
        placeholders = ", ".join(["?"] * len(values))
        stmt = f"INSERT INTO {_slug(schema.name)} ({columns_clause}) VALUES ({placeholders})"
        try:
            self.conn.execute(stmt, values)
            if not self.conn.in_transaction:
                self.conn.commit()
        except sqlite3.IntegrityError as err:
            raise Namel3ssError(f"Record '{schema.name}' violates constraints: {err}") from err
        rec = dict(record)
        rec[id_col] = self.conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        return rec

    def find(self, schema: RecordSchema, predicate) -> List[dict]:
        self._ensure_table(schema)
        if isinstance(predicate, dict):
            return self._find_by_filters(schema, predicate)
        cursor = self.conn.execute(f"SELECT * FROM {_slug(schema.name)}")
        rows = cursor.fetchall()
        results: List[dict] = []
        for row in rows:
            rec = self._deserialize_row(schema, row)
            if predicate(rec):
                results.append(rec)
        return results

    def list_records(self, schema: RecordSchema, limit: int = 20) -> List[dict]:
        self._ensure_table(schema)
        id_col = "id" if "id" in schema.field_map else "_id"
        cursor = self.conn.execute(f"SELECT * FROM {_slug(schema.name)} ORDER BY {id_col} ASC LIMIT ?", (limit,))
        return [self._deserialize_row(schema, row) for row in cursor.fetchall()]

    def check_unique(self, schema: RecordSchema, record: dict) -> str | None:
        self._ensure_table(schema)
        for field in schema.unique_fields:
            val = record.get(field)
            if val is None:
                continue
            col = _slug(field)
            cursor = self.conn.execute(
                f"SELECT 1 FROM {_slug(schema.name)} WHERE {col} = ? LIMIT 1",
                (self._serialize_value(schema.field_map[field].type_name, val),),
            )
            if cursor.fetchone():
                return field
        return None

    def _find_by_filters(self, schema: RecordSchema, filters: dict[str, Any]) -> List[dict]:
        where_clause, params = self._build_where_clause(schema, filters)
        table = _slug(schema.name)
        sql = f"SELECT * FROM {table}"
        if where_clause:
            sql += f" WHERE {where_clause}"
        cursor = self.conn.execute(sql, params)
        return [self._deserialize_row(schema, row) for row in cursor.fetchall()]

    def _build_where_clause(self, schema: RecordSchema, filters: dict[str, Any]) -> tuple[str, list[Any]]:
        parts: list[str] = []
        params: list[Any] = []
        for field, expected in filters.items():
            col = _slug(field)
            field_schema = schema.field_map.get(field)
            if field_schema is None:
                raise Namel3ssError(f"Unknown field '{field}' for record '{schema.name}'")
            if isinstance(expected, Contains):
                parts.append(f"{col} LIKE ? ESCAPE '\\'")
                params.append(f"%{_escape_like(expected.value)}%")
                continue
            parts.append(f"{col} = ?")
            params.append(self._serialize_value(field_schema.type_name if field_schema else "text", expected))
        return " AND ".join(parts), params

    def load_state(self) -> dict:
        row = self.conn.execute("SELECT payload FROM app_state WHERE id = 1").fetchone()
        if row is None:
            return {}
        try:
            return json.loads(row["payload"])
        except Exception:
            return {}

    def save_state(self, state: dict) -> None:
        payload = json.dumps(state)
        self.conn.execute(
            "INSERT INTO app_state (id, payload) VALUES (1, ?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload",
            (payload,),
        )
        self.conn.commit()

    def close(self) -> None:
        try:
            self.conn.close()
        except Exception:
            pass

    def get_metadata(self) -> PersistenceMetadata:
        return PersistenceMetadata(
            enabled=True,
            kind="sqlite",
            path=str(self.db_path),
            schema_version=SCHEMA_VERSION,
        )


def _escape_like(value: str) -> str:
    # Escape %, _, and backslash for LIKE patterns.
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
