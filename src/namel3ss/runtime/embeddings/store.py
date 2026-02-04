from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from namel3ss.config.model import AppConfig
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.persistence_paths import resolve_writable_path


@dataclass(frozen=True)
class EmbeddingRecord:
    chunk_id: str
    chunk_hash: str
    model_id: str
    dims: int
    vector: list[float] | None
    status: str


class EmbeddingStore:
    def get_records(self, *, model_id: str, chunk_hashes: list[str]) -> dict[str, EmbeddingRecord]:
        raise NotImplementedError

    def write_records(self, records: list[EmbeddingRecord]) -> None:
        raise NotImplementedError


class MemoryEmbeddingStore(EmbeddingStore):
    def __init__(self) -> None:
        self._records: dict[tuple[str, str], EmbeddingRecord] = {}

    def get_records(self, *, model_id: str, chunk_hashes: list[str]) -> dict[str, EmbeddingRecord]:
        output: dict[str, EmbeddingRecord] = {}
        for chunk_hash in chunk_hashes:
            record = self._records.get((model_id, chunk_hash))
            if record is not None:
                output[chunk_hash] = record
        return output

    def write_records(self, records: list[EmbeddingRecord]) -> None:
        for record in records:
            key = (record.model_id, record.chunk_hash)
            if key in self._records:
                continue
            self._records[key] = record


class SQLiteEmbeddingStore(EmbeddingStore):
    def __init__(self, db_path: Path) -> None:
        import sqlite3

        self.db_path = db_path
        try:
            self.conn = sqlite3.connect(self.db_path, isolation_level=None)
        except sqlite3.Error as err:
            raise Namel3ssError(f"Could not open SQLite embedding store: {err}") from err
        self.conn.row_factory = sqlite3.Row
        self._ensure_table()

    def _ensure_table(self) -> None:
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS embedding_vectors ("
            "chunk_hash TEXT NOT NULL,"
            "model_id TEXT NOT NULL,"
            "chunk_id TEXT NOT NULL,"
            "dims INTEGER NOT NULL,"
            "vector TEXT,"
            "status TEXT NOT NULL,"
            "PRIMARY KEY (chunk_hash, model_id)"
            ")"
        )

    def get_records(self, *, model_id: str, chunk_hashes: list[str]) -> dict[str, EmbeddingRecord]:
        if not chunk_hashes:
            return {}
        placeholders = ",".join(["?"] * len(chunk_hashes))
        sql = (
            "SELECT chunk_hash, chunk_id, model_id, dims, vector, status "
            "FROM embedding_vectors WHERE model_id = ? AND chunk_hash IN (" + placeholders + ")"
        )
        rows = self.conn.execute(sql, [model_id, *chunk_hashes]).fetchall()
        output: dict[str, EmbeddingRecord] = {}
        for row in rows:
            record = _decode_record(
                chunk_hash=row["chunk_hash"],
                chunk_id=row["chunk_id"],
                model_id=row["model_id"],
                dims=row["dims"],
                vector=row["vector"],
                status=row["status"],
            )
            output[record.chunk_hash] = record
        return output

    def write_records(self, records: list[EmbeddingRecord]) -> None:
        if not records:
            return
        sql = (
            "INSERT OR IGNORE INTO embedding_vectors "
            "(chunk_hash, model_id, chunk_id, dims, vector, status) VALUES (?, ?, ?, ?, ?, ?)"
        )
        for record in records:
            vector_text = _encode_vector(record.vector)
            self.conn.execute(
                sql,
                (
                    record.chunk_hash,
                    record.model_id,
                    record.chunk_id,
                    record.dims,
                    vector_text,
                    record.status,
                ),
            )


class PostgresEmbeddingStore(EmbeddingStore):
    def __init__(self, database_url: str) -> None:
        try:
            import psycopg
            from psycopg.rows import dict_row
        except Exception as err:
            raise Namel3ssError(_missing_driver_message()) from err
        try:
            self.conn = psycopg.connect(database_url, row_factory=dict_row)
        except Exception as err:
            raise Namel3ssError("Could not open Postgres embedding store.") from err
        self.conn.autocommit = False
        self._ensure_table()

    def _ensure_table(self) -> None:
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS embedding_vectors ("
            "chunk_hash TEXT NOT NULL,"
            "model_id TEXT NOT NULL,"
            "chunk_id TEXT NOT NULL,"
            "dims INTEGER NOT NULL,"
            "vector TEXT,"
            "status TEXT NOT NULL,"
            "PRIMARY KEY (chunk_hash, model_id)"
            ")"
        )
        self.conn.commit()

    def get_records(self, *, model_id: str, chunk_hashes: list[str]) -> dict[str, EmbeddingRecord]:
        if not chunk_hashes:
            return {}
        rows = self.conn.execute(
            "SELECT chunk_hash, chunk_id, model_id, dims, vector, status "
            "FROM embedding_vectors WHERE model_id = %s AND chunk_hash = ANY(%s)",
            (model_id, chunk_hashes),
        ).fetchall()
        output: dict[str, EmbeddingRecord] = {}
        for row in rows:
            record = _decode_record(
                chunk_hash=row["chunk_hash"],
                chunk_id=row["chunk_id"],
                model_id=row["model_id"],
                dims=row["dims"],
                vector=row["vector"],
                status=row["status"],
            )
            output[record.chunk_hash] = record
        return output

    def write_records(self, records: list[EmbeddingRecord]) -> None:
        if not records:
            return
        sql = (
            "INSERT INTO embedding_vectors (chunk_hash, model_id, chunk_id, dims, vector, status) "
            "VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (chunk_hash, model_id) DO NOTHING"
        )
        for record in records:
            vector_text = _encode_vector(record.vector)
            self.conn.execute(
                sql,
                (
                    record.chunk_hash,
                    record.model_id,
                    record.chunk_id,
                    record.dims,
                    vector_text,
                    record.status,
                ),
            )
        self.conn.commit()


_MEMORY_STORES: dict[str, MemoryEmbeddingStore] = {}


def get_embedding_store(
    config: AppConfig | None,
    *,
    project_root: str | None,
    app_path: str | None,
) -> EmbeddingStore:
    cfg = config or AppConfig()
    target = str(cfg.persistence.target or "memory").strip().lower()
    if target in {"memory", "mem", "none", "off"}:
        scope = _scope_key(project_root, app_path)
        store = _MEMORY_STORES.get(scope)
        if store is None:
            store = MemoryEmbeddingStore()
            _MEMORY_STORES[scope] = store
        return store
    if target == "sqlite":
        db_path = resolve_writable_path(Path(cfg.persistence.db_path or ".namel3ss/data.db"))
        return SQLiteEmbeddingStore(db_path)
    if target == "postgres":
        url = cfg.persistence.database_url or ""
        if not url:
            raise Namel3ssError(_missing_postgres_url_message())
        return PostgresEmbeddingStore(url)
    raise Namel3ssError(_unsupported_target_message(target))


def _encode_vector(vector: list[float] | None) -> str | None:
    if vector is None:
        return None
    return json.dumps([float(value) for value in vector], separators=(",", ":"), ensure_ascii=True)


def _decode_record(
    *,
    chunk_hash: str,
    chunk_id: str,
    model_id: str,
    dims: Any,
    vector: Any,
    status: Any,
) -> EmbeddingRecord:
    status_value = str(status or "").strip().lower()
    if status_value not in {"ok", "unavailable"}:
        raise Namel3ssError(_status_message(status_value))
    dims_value = _coerce_int(dims)
    if dims_value is None or dims_value <= 0:
        raise Namel3ssError(_dims_message())
    vector_value: list[float] | None = None
    if status_value == "ok":
        vector_value = _decode_vector(vector)
    return EmbeddingRecord(
        chunk_id=str(chunk_id),
        chunk_hash=str(chunk_hash),
        model_id=str(model_id),
        dims=dims_value,
        vector=vector_value,
        status=status_value,
    )


def _decode_vector(raw: Any) -> list[float]:
    if raw is None:
        raise Namel3ssError(_vector_message("missing vector data"))
    try:
        parsed = json.loads(raw) if isinstance(raw, str) else raw
    except Exception as err:
        raise Namel3ssError(_vector_message(f"invalid JSON: {err}")) from err
    if not isinstance(parsed, list):
        raise Namel3ssError(_vector_message("expected a list of numbers"))
    values: list[float] = []
    for item in parsed:
        if isinstance(item, bool):
            raise Namel3ssError(_vector_message("vector values must be numbers"))
        try:
            values.append(float(item))
        except Exception as err:
            raise Namel3ssError(_vector_message(f"invalid value: {err}")) from err
    return values


def _coerce_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    try:
        return int(value)
    except Exception:
        return None


def _scope_key(project_root: str | None, app_path: str | None) -> str:
    raw = f"{project_root or ''}|{app_path or ''}"
    digest = sha256(raw.encode("utf-8")).hexdigest()
    return digest[:16]


def _missing_driver_message() -> str:
    return build_guidance_message(
        what="Postgres embeddings require a driver.",
        why="The postgres extra is not installed.",
        fix="Install the postgres extra.",
        example='pip install "namel3ss[postgres]"',
    )


def _missing_postgres_url_message() -> str:
    return build_guidance_message(
        what="Postgres embedding store is missing N3_DATABASE_URL.",
        why="Embedding persistence needs a database URL.",
        fix="Set N3_DATABASE_URL or configure persistence.database_url.",
        example="N3_PERSIST_TARGET=postgres N3_DATABASE_URL=postgres://user:pass@host/db",
    )


def _unsupported_target_message(target: str) -> str:
    return build_guidance_message(
        what=f"Embedding persistence target '{target}' is not supported.",
        why="Embeddings require sqlite or postgres persistence, or memory for local runs.",
        fix="Set persistence.target to sqlite, postgres, or memory.",
        example='[persistence]\ntarget = "sqlite"',
    )


def _status_message(value: str) -> str:
    return build_guidance_message(
        what=f"Embedding status '{value}' is invalid.",
        why="Embedding status must be ok or unavailable.",
        fix="Re-run ingestion to rebuild embeddings.",
        example='{"status":"ok"}',
    )


def _dims_message() -> str:
    return build_guidance_message(
        what="Embedding dims are invalid.",
        why="Stored vectors must include a positive dimension count.",
        fix="Re-run ingestion with a valid embedding configuration.",
        example='[embedding]\ndims = 64',
    )


def _vector_message(reason: str) -> str:
    return build_guidance_message(
        what="Embedding vector payload is invalid.",
        why=f"Vector parsing failed: {reason}.",
        fix="Re-run ingestion to rebuild embeddings.",
        example='{"status":"ok","vector":[0.1,0.2]}',
    )


__all__ = [
    "EmbeddingRecord",
    "EmbeddingStore",
    "MemoryEmbeddingStore",
    "PostgresEmbeddingStore",
    "SQLiteEmbeddingStore",
    "get_embedding_store",
]
