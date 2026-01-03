from __future__ import annotations

from pathlib import Path

from namel3ss.config.loader import load_config
from namel3ss.config.model import AppConfig
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.store.memory_store import MemoryStore
from namel3ss.runtime.storage.postgres_store import PostgresStore
from namel3ss.runtime.storage.sqlite_store import SQLiteStore
from namel3ss.runtime.persistence_paths import resolve_writable_path
from namel3ss.secrets import record_secret_access


DEFAULT_DB_PATH = Path(".namel3ss/data.db")


def create_store(db_path: Path | None = None, config: AppConfig | None = None):
    cfg = config or load_config()
    target = (cfg.persistence.target or "memory").strip().lower()
    if target == "memory":
        return MemoryStore()
    if target == "sqlite":
        path = db_path or Path(cfg.persistence.db_path or DEFAULT_DB_PATH)
        resolved = resolve_writable_path(path)
        return SQLiteStore(resolved)
    if target == "postgres":
        url = cfg.persistence.database_url or ""
        if not url:
            raise Namel3ssError(_missing_postgres_url_message())
        record_secret_access("N3_DATABASE_URL", caller="persistence:postgres", source="env")
        return PostgresStore(url)
    if target == "edge":
        raise Namel3ssError(_edge_stub_message())
    raise Namel3ssError(_unsupported_target_message(target))


def resolve_store(store=None, config: AppConfig | None = None):
    return store if store is not None else create_store(config=config)


def _missing_postgres_url_message() -> str:
    return build_guidance_message(
        what="Postgres persistence target is missing N3_DATABASE_URL.",
        why="Postgres mode needs a connection string to open the database.",
        fix="Set N3_DATABASE_URL to a valid postgres:// URL.",
        example="N3_PERSIST_TARGET=postgres N3_DATABASE_URL=postgres://user:pass@host/db",
    )


def _edge_stub_message() -> str:
    return build_guidance_message(
        what="Edge persistence target is not implemented yet.",
        why="The edge adapter is a placeholder in this alpha release.",
        fix="Use sqlite for local dev or postgres for production.",
        example="N3_PERSIST_TARGET=sqlite",
    )


def _unsupported_target_message(target: str) -> str:
    return build_guidance_message(
        what=f"Unsupported persistence target '{target}'.",
        why="Targets must be one of sqlite, postgres, edge, or memory.",
        fix="Set N3_PERSIST_TARGET to a supported value.",
        example="N3_PERSIST_TARGET=sqlite",
    )
