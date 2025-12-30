from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import urlsplit, urlunsplit

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.schema.records import EXPIRES_AT_FIELD, TENANT_KEY_FIELD, RecordSchema
from namel3ss.runtime.storage.metadata import PersistenceMetadata
from namel3ss.runtime.store.memory_store import Contains
from namel3ss.runtime.storage.state_codec import decode_state, encode_state
from namel3ss.runtime.storage.base import RecordScope
from namel3ss.runtime.storage.predicate import PredicatePlan
from namel3ss.runtime.storage.sql_helpers import escape_like, quote_identifier, slug_identifier
from namel3ss.utils.json_tools import dumps as json_dumps
from namel3ss.utils.numbers import decimal_is_int, is_number, to_decimal


SCHEMA_VERSION = 1


class PostgresStore:
    def __init__(self, database_url: str) -> None:
        try:
            import psycopg
            from psycopg.rows import dict_row
        except Exception as err:
            raise Namel3ssError(_missing_driver_message()) from err
        try:
            self.conn = psycopg.connect(database_url, row_factory=dict_row)
        except Exception as err:
            raise Namel3ssError(f"Could not open Postgres store: {err}") from err
        self.dialect = "postgres"
        self.conn.autocommit = False
        self.database_url = database_url
        self._prepared_tables: set[str] = set()
        self._prepared_indexes: Dict[str, set[str]] = {}
        self._apply_settings()
        self._ensure_schema_version()

    def begin(self) -> None:
        self.conn.execute("BEGIN")

    def commit(self) -> None:
        self.conn.commit()

    def rollback(self) -> None:
        self.conn.rollback()

    def clear(self) -> None:
        tables = self._list_tables()
        for table in tables:
            self.conn.execute(f"DROP TABLE IF EXISTS {quote_identifier(table)} CASCADE")
        self.conn.commit()
        self._prepared_tables.clear()
        self._prepared_indexes.clear()
        self._ensure_schema_version()

    def _apply_settings(self) -> None:
        try:
            self.conn.execute("SET TIME ZONE 'UTC'")
        except Exception:
            pass

    def _ensure_schema_version(self) -> None:
        self.conn.execute("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL)")
        row = self.conn.execute("SELECT version FROM schema_version LIMIT 1").fetchone()
        if row is None:
            self.conn.execute("INSERT INTO schema_version (version) VALUES (%s)", (SCHEMA_VERSION,))
            self.conn.commit()
        elif row["version"] < SCHEMA_VERSION:
            self._migrate(int(row["version"]))
        elif row["version"] > SCHEMA_VERSION:
            raise Namel3ssError(
                f"Unsupported schema version {row['version']} in Postgres store. Expected {SCHEMA_VERSION}."
            )
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS app_state (id INTEGER PRIMARY KEY CHECK (id = 1), payload TEXT NOT NULL)"
        )
        self.conn.commit()

    def _migrate(self, current_version: int) -> None:
        if current_version < 1 or current_version > SCHEMA_VERSION:
            raise Namel3ssError(
                f"Cannot migrate unknown schema version {current_version} (target {SCHEMA_VERSION})."
            )
        self.conn.execute("UPDATE schema_version SET version = %s", (SCHEMA_VERSION,))
        self.conn.commit()

    def _ensure_table(self, schema: RecordSchema) -> None:
        table = slug_identifier(schema.name)
        if table not in self._prepared_tables:
            id_col = "id" if "id" in schema.field_map else "_id"
            columns = [f"{quote_identifier(id_col)} BIGSERIAL PRIMARY KEY"]
            for field in schema.storage_fields():
                col_name = slug_identifier(field.name)
                col_type = self._sql_type(field.type_name)
                if col_name == id_col:
                    continue
                columns.append(f"{quote_identifier(col_name)} {col_type}")
            stmt = f"CREATE TABLE IF NOT EXISTS {quote_identifier(table)} ({', '.join(columns)})"
            self.conn.execute(stmt)
            self._prepared_tables.add(table)
        self._ensure_columns(schema)
        self._ensure_indexes(schema)
        self.conn.commit()

    def _ensure_columns(self, schema: RecordSchema) -> None:
        table = slug_identifier(schema.name)
        existing = self._existing_columns(table)
        id_col = "id" if "id" in schema.field_map else "_id"
        for field in schema.storage_fields():
            col_name = slug_identifier(field.name)
            if col_name == id_col or col_name in existing:
                continue
            col_type = self._sql_type(field.type_name)
            self.conn.execute(
                f"ALTER TABLE {quote_identifier(table)} ADD COLUMN {quote_identifier(col_name)} {col_type}"
            )
        if not self.conn.autocommit:
            self.conn.commit()

    def _existing_columns(self, table: str) -> set[str]:
        rows = self.conn.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = %s",
            (table,),
        ).fetchall()
        return {row["column_name"] for row in rows}

    def _ensure_indexes(self, schema: RecordSchema) -> None:
        table = slug_identifier(schema.name)
        prepared = self._prepared_indexes.setdefault(table, set())
        if not prepared:
            prepared.update(self._existing_indexes(table))
        tenant_col = slug_identifier(TENANT_KEY_FIELD) if schema.tenant_key else None
        for field in schema.unique_fields:
            col = slug_identifier(field)
            if tenant_col:
                index_name = self._index_name(table, f"{tenant_col}_{col}")
            else:
                index_name = self._index_name(table, col)
            if index_name in prepared:
                continue
            if tenant_col:
                columns = f"{quote_identifier(tenant_col)}, {quote_identifier(col)}"
            else:
                columns = f"{quote_identifier(col)}"
            self.conn.execute(
                f"CREATE UNIQUE INDEX IF NOT EXISTS {quote_identifier(index_name)} "
                f"ON {quote_identifier(table)} ({columns})"
            )
            prepared.add(index_name)

    def _existing_indexes(self, table: str) -> set[str]:
        rows = self.conn.execute(
            "SELECT indexname FROM pg_indexes WHERE schemaname = 'public' AND tablename = %s",
            (table,),
        ).fetchall()
        return {row["indexname"] for row in rows}

    def _index_name(self, table: str, column: str) -> str:
        return f"idx_{table}_{column}_uniq"

    def _sql_type(self, type_name: str) -> str:
        name = type_name.lower()
        if name in {"string", "str", "text", "json"}:
            return "TEXT"
        if name in {"int", "integer"}:
            return "BIGINT"
        if name == "boolean" or name == "bool":
            return "BOOLEAN"
        if name == "number":
            return "NUMERIC"
        return "TEXT"

    def _serialize_value(self, type_name: str, value):
        name = type_name.lower()
        if name in {"string", "str", "text"}:
            return value
        if name in {"int", "integer"}:
            if value is None:
                return None
            if isinstance(value, Decimal):
                if not decimal_is_int(value):
                    raise Namel3ssError(f"Expected integer value for {type_name}, got {value}")
                return int(value)
            return int(value)
        if name == "number":
            if value is None:
                return None
            if is_number(value):
                return to_decimal(value)
            return value
        if name in {"boolean", "bool"}:
            return None if value is None else bool(value)
        if name == "json":
            return json_dumps(value) if value is not None else None
        return value

    def _deserialize_row(self, schema: RecordSchema, row: dict) -> dict:
        data: dict = {}
        for field in schema.fields:
            col = slug_identifier(field.name)
            if col not in row:
                continue
            val = row[col]
            if field.type_name.lower() in {"boolean", "bool"}:
                data[field.name] = bool(val) if val is not None else None
                continue
            if field.type_name.lower() == "number":
                data[field.name] = Decimal(str(val)) if val is not None else None
                continue
            if field.type_name.lower() == "json" and val is not None:
                try:
                    data[field.name] = json.loads(val)
                except Exception:
                    data[field.name] = val
                continue
            if field.type_name.lower() in {"int", "integer"}:
                data[field.name] = int(val) if val is not None else None
                continue
            data[field.name] = val
        id_col = "id" if "id" in schema.field_map else "_id"
        if id_col in row:
            data[id_col] = row[id_col]
        return data

    def save(self, schema: RecordSchema, record: dict) -> dict:
        self._ensure_table(schema)
        id_col = "id" if "id" in schema.field_map else "_id"
        col_names = []
        values = []
        for field in schema.storage_fields():
            if field.name == id_col:
                continue
            col_names.append(quote_identifier(slug_identifier(field.name)))
            values.append(self._serialize_value(field.type_name, record.get(field.name)))
        columns_clause = ", ".join(col_names)
        placeholders = ", ".join(["%s"] * len(values))
        stmt = (
            f"INSERT INTO {quote_identifier(slug_identifier(schema.name))} ({columns_clause}) "
            f"VALUES ({placeholders}) RETURNING {quote_identifier(id_col)}"
        )
        try:
            cursor = self.conn.execute(stmt, values)
        except Exception as err:
            raise Namel3ssError(f"Record '{schema.name}' violates constraints: {err}") from err
        rec = dict(record)
        row = cursor.fetchone()
        if row is not None:
            rec[id_col] = row[id_col]
        if not self.conn.autocommit:
            self.conn.commit()
        return rec

    def update(self, schema: RecordSchema, record: dict) -> dict:
        self._ensure_table(schema)
        id_col = "id" if "id" in schema.field_map else "_id"
        if id_col not in record:
            raise Namel3ssError(f"Record '{schema.name}' update requires {id_col}")
        assignments = []
        values = []
        for field in schema.fields:
            if field.name == id_col:
                continue
            assignments.append(f"{quote_identifier(slug_identifier(field.name))} = %s")
            values.append(self._serialize_value(field.type_name, record.get(field.name)))
        values.append(record[id_col])
        stmt = (
            f"UPDATE {quote_identifier(slug_identifier(schema.name))} SET {', '.join(assignments)} "
            f"WHERE {quote_identifier(id_col)} = %s"
        )
        try:
            cursor = self.conn.execute(stmt, values)
        except Exception as err:
            raise Namel3ssError(f"Record '{schema.name}' violates constraints: {err}") from err
        if cursor.rowcount == 0:
            raise Namel3ssError(f"Record '{schema.name}' with {id_col}={record[id_col]} was not found")
        if not self.conn.autocommit:
            self.conn.commit()
        return record

    def delete(self, schema: RecordSchema, record_id: object) -> bool:
        self._ensure_table(schema)
        id_col = "id" if "id" in schema.field_map else "_id"
        stmt = f"DELETE FROM {quote_identifier(slug_identifier(schema.name))} WHERE {quote_identifier(id_col)} = %s"
        cursor = self.conn.execute(stmt, [record_id])
        if not self.conn.autocommit:
            self.conn.commit()
        return cursor.rowcount > 0

    def find(self, schema: RecordSchema, predicate, scope: RecordScope | None = None) -> List[dict]:
        scope = scope or RecordScope()
        self._ensure_table(schema)
        self._cleanup_expired(schema, scope)
        if isinstance(predicate, PredicatePlan):
            if predicate.sql:
                scope_clause, scope_params = self._scope_where(schema, scope)
                clauses = [clause for clause in [scope_clause, predicate.sql.clause] if clause]
                sql = f"SELECT * FROM {quote_identifier(slug_identifier(schema.name))}"
                if clauses:
                    sql += " WHERE " + " AND ".join(clauses)
                cursor = self.conn.execute(sql, [*scope_params, *predicate.sql.params])
                return [self._deserialize_row(schema, row) for row in cursor.fetchall()]
            predicate = predicate.predicate
        if isinstance(predicate, dict):
            return self._find_by_filters(schema, predicate, scope)
        where_clause, params = self._scope_where(schema, scope)
        sql = f"SELECT * FROM {quote_identifier(slug_identifier(schema.name))}"
        if where_clause:
            sql += f" WHERE {where_clause}"
        cursor = self.conn.execute(sql, params)
        rows = cursor.fetchall()
        results: List[dict] = []
        for row in rows:
            rec = self._deserialize_row(schema, row)
            if predicate(rec):
                results.append(rec)
        return results

    def list_records(self, schema: RecordSchema, limit: int = 20, scope: RecordScope | None = None) -> List[dict]:
        scope = scope or RecordScope()
        self._ensure_table(schema)
        self._cleanup_expired(schema, scope)
        id_col = "id" if "id" in schema.field_map else "_id"
        where_clause, params = self._scope_where(schema, scope)
        sql = (
            f"SELECT * FROM {quote_identifier(slug_identifier(schema.name))} "
            f"ORDER BY {quote_identifier(id_col)} ASC LIMIT %s"
        )
        params = list(params) + [limit]
        if where_clause:
            sql = (
                f"SELECT * FROM {quote_identifier(slug_identifier(schema.name))} "
                f"WHERE {where_clause} ORDER BY {quote_identifier(id_col)} ASC LIMIT %s"
            )
        cursor = self.conn.execute(sql, params)
        return [self._deserialize_row(schema, row) for row in cursor.fetchall()]

    def check_unique(self, schema: RecordSchema, record: dict, scope: RecordScope | None = None) -> str | None:
        scope = scope or RecordScope()
        self._ensure_table(schema)
        self._cleanup_expired(schema, scope)
        tenant_value = record.get(TENANT_KEY_FIELD)
        for field in schema.unique_fields:
            val = record.get(field)
            if val is None:
                continue
            col = slug_identifier(field)
            clauses = [f"{quote_identifier(col)} = %s"]
            params = [self._serialize_value(schema.field_map[field].type_name, val)]
            if schema.tenant_key:
                tenant_col = slug_identifier(TENANT_KEY_FIELD)
                clauses.append(f"{quote_identifier(tenant_col)} = %s")
                params.append(tenant_value)
            ttl_clause, ttl_params = self._ttl_clause(schema, scope)
            if ttl_clause:
                clauses.append(ttl_clause)
                params.extend(ttl_params)
            where_clause = " AND ".join(clauses)
            cursor = self.conn.execute(
                f"SELECT 1 FROM {quote_identifier(slug_identifier(schema.name))} WHERE {where_clause} LIMIT 1",
                params,
            )
            if cursor.fetchone():
                return field
        return None

    def _find_by_filters(self, schema: RecordSchema, filters: dict[str, Any], scope: RecordScope) -> List[dict]:
        scope_clause, scope_params = self._scope_where(schema, scope)
        where_clause, params = self._build_where_clause(schema, filters)
        table = quote_identifier(slug_identifier(schema.name))
        clauses = [clause for clause in [scope_clause, where_clause] if clause]
        sql = f"SELECT * FROM {table}"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        cursor = self.conn.execute(sql, [*scope_params, *params])
        return [self._deserialize_row(schema, row) for row in cursor.fetchall()]

    def _build_where_clause(self, schema: RecordSchema, filters: dict[str, Any]) -> tuple[str, list[Any]]:
        parts: list[str] = []
        params: list[Any] = []
        for field, expected in filters.items():
            col = slug_identifier(field)
            field_schema = schema.field_map.get(field)
            if field_schema is None:
                raise Namel3ssError(f"Unknown field '{field}' for record '{schema.name}'")
            if isinstance(expected, Contains):
                parts.append(f"{quote_identifier(col)} LIKE %s ESCAPE '\\\\'")
                params.append(f"%{escape_like(expected.value)}%")
                continue
            parts.append(f"{quote_identifier(col)} = %s")
            params.append(self._serialize_value(field_schema.type_name if field_schema else "text", expected))
        return " AND ".join(parts), params

    def _scope_where(self, schema: RecordSchema, scope: RecordScope) -> tuple[str, list[Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if schema.tenant_key and scope.tenant_value is not None:
            tenant_col = slug_identifier(TENANT_KEY_FIELD)
            clauses.append(f"{quote_identifier(tenant_col)} = %s")
            params.append(scope.tenant_value)
        ttl_clause, ttl_params = self._ttl_clause(schema, scope)
        if ttl_clause:
            clauses.append(ttl_clause)
            params.extend(ttl_params)
        return " AND ".join(clauses), params

    def _ttl_clause(self, schema: RecordSchema, scope: RecordScope) -> tuple[str, list[Any]]:
        if schema.ttl_hours is None or scope.now is None:
            return "", []
        col = quote_identifier(slug_identifier(EXPIRES_AT_FIELD))
        return f"{col} IS NOT NULL AND {col} > %s", [scope.now]

    def _cleanup_expired(self, schema: RecordSchema, scope: RecordScope) -> None:
        if schema.ttl_hours is None or scope.now is None:
            return
        table = quote_identifier(slug_identifier(schema.name))
        col = quote_identifier(slug_identifier(EXPIRES_AT_FIELD))
        self.conn.execute(
            f"DELETE FROM {table} WHERE {col} IS NULL OR {col} <= %s",
            (scope.now,),
        )
        if not self.conn.autocommit:
            self.conn.commit()

    def load_state(self) -> dict:
        row = self.conn.execute("SELECT payload FROM app_state WHERE id = 1").fetchone()
        if row is None:
            return {}
        try:
            decoded = json.loads(row["payload"])
            return decode_state(decoded)
        except Exception:
            return {}

    def save_state(self, state: dict) -> None:
        payload = json.dumps(encode_state(state))
        self.conn.execute(
            "INSERT INTO app_state (id, payload) VALUES (1, %s) "
            "ON CONFLICT (id) DO UPDATE SET payload = EXCLUDED.payload",
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
            kind="postgres",
            path=_redact_url(self.database_url),
            schema_version=SCHEMA_VERSION,
        )

    def _list_tables(self) -> list[str]:
        rows = self.conn.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
        ).fetchall()
        return [row["tablename"] for row in rows]
def _missing_driver_message() -> str:
    return build_guidance_message(
        what="Postgres persistence requires a driver.",
        why="psycopg is not installed, so namel3ss cannot open a Postgres connection.",
        fix="Install the postgres extra.",
        example="pip install \"namel3ss[postgres]\"",
    )


def _redact_url(raw: str) -> str:
    if not raw:
        return raw
    try:
        parts = urlsplit(raw)
    except Exception:
        return raw
    if "@" not in parts.netloc:
        return raw
    userinfo, host = parts.netloc.rsplit("@", 1)
    if ":" in userinfo:
        user, _ = userinfo.split(":", 1)
        userinfo = f"{user}:***"
    else:
        userinfo = "***"
    netloc = f"{userinfo}@{host}"
    return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))
