from __future__ import annotations

from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from namel3ss.config.model import AppConfig
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.data.backend_interface import BackendDescriptor, register_backend


def _replica_descriptors(config: AppConfig) -> tuple[str, ...]:
    raw = list(getattr(config.persistence, "replica_urls", []) or [])
    return tuple("url set" if str(value or "").strip() else "url missing" for value in raw)


def normalize_mysql_error(err: Exception) -> str:
    code = None
    args = getattr(err, "args", None)
    if isinstance(args, tuple) and args:
        first = args[0]
        if isinstance(first, int):
            code = first
    if code == 1062:
        return "duplicate key"
    if code == 1146:
        return "missing table"
    if code == 1054:
        return "unknown column"
    if code is not None:
        return f"mysql error {code}"
    return "mysql error"


def quote_mysql_identifier(name: str) -> str:
    escaped = name.replace("`", "``")
    return f"`{escaped}`"


def mysql_missing_driver_message() -> str:
    return build_guidance_message(
        what="MySQL persistence requires a driver.",
        why="pymysql is not installed, so namel3ss cannot open a MySQL connection.",
        fix="Install the mysql extra.",
        example="pip install \"namel3ss[mysql]\"",
    )


def redact_mysql_url(raw: str) -> str:
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


def parse_mysql_url(database_url: str) -> dict:
    parts = urlsplit(database_url)
    if not parts.scheme or not parts.hostname:
        raise ValueError("MySQL URL is missing a host.")
    if parts.scheme not in {"mysql", "mariadb"}:
        raise ValueError("MySQL URL must start with mysql:// or mariadb://.")
    database = parts.path.lstrip("/") if parts.path else ""
    if not database:
        raise ValueError("MySQL URL is missing a database name.")
    return {
        "host": parts.hostname,
        "user": parts.username or "",
        "password": parts.password or "",
        "database": database,
        "port": parts.port or 3306,
        "charset": "utf8mb4",
    }


class MySQLBackend:
    name = "mysql"

    def describe(self, config: AppConfig, *, project_root: Path | None) -> BackendDescriptor:
        descriptor = "mysql url set" if config.persistence.database_url else "mysql url missing"
        return BackendDescriptor(
            target="mysql",
            kind="mysql",
            enabled=True,
            descriptor=descriptor,
            replicas=_replica_descriptors(config),
        )

    def sql_type_for(self, type_name: str) -> str:
        name = type_name.lower()
        if name in {"string", "str", "text", "json"}:
            return "TEXT"
        if name in {"int", "integer"}:
            return "BIGINT"
        if name in {"boolean", "bool"}:
            return "TINYINT(1)"
        if name == "number":
            return "DECIMAL(38,18)"
        return "TEXT"

    def normalize_error(self, err: Exception) -> str:
        return normalize_mysql_error(err)


register_backend(MySQLBackend())


__all__ = [
    "MySQLBackend",
    "mysql_missing_driver_message",
    "normalize_mysql_error",
    "parse_mysql_url",
    "quote_mysql_identifier",
    "redact_mysql_url",
]
