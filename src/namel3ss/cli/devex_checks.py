from __future__ import annotations

import importlib.util
import os
import shutil
import sys
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from namel3ss.cli.doctor_models import DoctorCheck
from namel3ss.config.loader import ConfigSource
from namel3ss.config.model import AppConfig
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.resources import studio_web_root
from namel3ss.version import get_version

MIN_PYTHON = (3, 10)
SUPPORTED_PYTHON_RANGE = ">=3.10"
STATUS_ICONS = {"ok": "✅", "warning": "⚠️", "error": "❌"}
RESERVED_TRUE_VALUES = {"1", "true", "yes", "on"}
SUPPORTED_TARGETS = {"memory", "sqlite", "postgres", "edge"}
STUDIO_ASSETS = ["index.html", "app.js", "styles.css"]


def status_icon(status: str) -> str:
    return STATUS_ICONS.get(status, "⚠️")


def python_check() -> DoctorCheck:
    version_tuple = sys.version_info[:3]
    version_str = ".".join(map(str, version_tuple))
    supported = version_tuple >= MIN_PYTHON
    status = "ok" if supported else "error"
    message = f"Python {version_str} requires {SUPPORTED_PYTHON_RANGE}"
    fix = "Install Python 3.10+ and re-run `pip install namel3ss`."
    return DoctorCheck(id="python_version", category="environment", code="python.version", status=status, message=message, fix=fix)


def import_path_check() -> DoctorCheck:
    spec = importlib.util.find_spec("namel3ss")
    origin = Path(spec.origin).resolve() if spec and spec.origin else None
    pythonpath = os.getenv("PYTHONPATH") or ""
    shadowed = _find_shadow_paths(origin)
    if shadowed:
        message = f"namel3ss import may be shadowed. Using {origin}, also found {', '.join(shadowed)}"
        fix = "Clear PYTHONPATH or remove extra namel3ss copies so the installed CLI is used."
        return DoctorCheck(
            id="import_path",
            category="environment",
            code="python.import_path.shadowed",
            status="warning",
            message=message,
            fix=fix,
        )
    if pythonpath:
        message = f"PYTHONPATH is set; current namel3ss import is {origin}"
        fix = "Unset PYTHONPATH or activate a clean virtualenv before running `n3`."
        return DoctorCheck(
            id="import_path",
            category="environment",
            code="python.import_path.pythonpath",
            status="warning",
            message=message,
            fix=fix,
        )
    message = f"namel3ss import path: {origin}"
    fix = "No action needed."
    return DoctorCheck(id="import_path", category="environment", code="python.import_path.ok", status="ok", message=message, fix=fix)


def optional_dependencies_check(config: AppConfig | None) -> DoctorCheck:
    target = resolve_target(config)
    if target == "postgres" and not _has_postgres_driver():
        message = "Postgres driver missing. psycopg not installed."
        fix = "Install postgres support with pip, then re-run n3 doctor."
        return DoctorCheck(
            id="optional_dependencies",
            category="environment",
            code="deps.postgres.missing",
            status="error",
            message=message,
            fix=fix,
        )
    message = "Optional dependencies: install psycopg only if you use Postgres."
    fix = "No action needed."
    return DoctorCheck(id="optional_dependencies", category="environment", code="deps.optional.ok", status="ok", message=message, fix=fix)


def persistence_check(config: AppConfig | None) -> DoctorCheck:
    target = resolve_target(config)
    if target not in SUPPORTED_TARGETS:
        message = f"Persistence target '{target}' is not supported."
        fix = "Set N3_PERSIST_TARGET to sqlite, postgres, edge, or memory."
        return DoctorCheck(id="persistence", category="project", code="persistence.invalid", status="error", message=message, fix=fix)
    if target == "memory":
        message = "Persistence disabled in memory store."
        fix = "Set N3_PERSIST_TARGET=sqlite to persist to .namel3ss/data.db."
        return DoctorCheck(id="persistence", category="project", code="persistence.memory", status="warning", message=message, fix=fix)
    if target == "sqlite":
        db_path = ".namel3ss/data.db"
        if config and config.persistence.db_path:
            db_path = config.persistence.db_path
        data_file = Path(db_path)
        data_dir = data_file.parent
        writable_dir = data_dir.exists() and os.access(data_dir, os.W_OK)
        writable_file = data_file.exists() and os.access(data_file, os.W_OK)
        can_create = not data_dir.exists() and os.access(Path.cwd(), os.W_OK)
        if (writable_dir or can_create) and (not data_file.exists() or writable_file):
            message = f"Persistence target sqlite, data path {data_file.as_posix()} writable."
            fix = "No action needed."
            status = "ok"
        else:
            message = f"Persistence target sqlite but {data_file.as_posix()} is not writable."
            fix = "Make the directory writable or set N3_DB_PATH to a writable location."
            status = "error"
        return DoctorCheck(id="persistence", category="project", code="persistence.sqlite", status=status, message=message, fix=fix)
    if target == "postgres":
        url = config.persistence.database_url if config else os.getenv("N3_DATABASE_URL")
        if not url:
            message = "Persistence target postgres but N3_DATABASE_URL is missing."
            fix = "Set N3_DATABASE_URL to a valid postgres:// URL."
            return DoctorCheck(id="persistence", category="project", code="persistence.postgres.missing", status="error", message=message, fix=fix)
        redacted = _redact_url(url)
        message = f"Persistence target postgres with N3_DATABASE_URL set {redacted}."
        fix = "No action needed."
        return DoctorCheck(id="persistence", category="project", code="persistence.postgres.ok", status="ok", message=message, fix=fix)
    if target == "edge":
        url = config.persistence.edge_kv_url if config else os.getenv("N3_EDGE_KV_URL")
        if not url:
            message = "Persistence target edge but N3_EDGE_KV_URL is missing."
            fix = "Set N3_EDGE_KV_URL or switch to sqlite/postgres."
            return DoctorCheck(id="persistence", category="project", code="persistence.edge.missing", status="error", message=message, fix=fix)
        redacted = _redact_url(url)
        message = f"Persistence target edge configured {redacted}."
        fix = "Use sqlite/postgres unless you are testing edge integrations."
        return DoctorCheck(id="persistence", category="project", code="persistence.edge.warning", status="warning", message=message, fix=fix)
    return DoctorCheck(id="persistence", category="project", code="persistence.unknown", status="warning", message="Persistence target unknown.", fix="Check N3_PERSIST_TARGET.")


def config_sources_check(sources: list[ConfigSource]) -> DoctorCheck:
    if not sources:
        message = "Config sources: defaults only. No env, .env, or namel3ss.toml."
        fix = "Add .env or namel3ss.toml for defaults, or set environment variables."
        return DoctorCheck(id="config_sources", category="project", code="config.sources.none", status="warning", message=message, fix=fix)
    parts = []
    for source in sources:
        if source.kind == "env":
            parts.append("env")
        elif source.path:
            parts.append(f"{source.kind} {source.path}")
        else:
            parts.append(source.kind)
    message = f"Config sources: {', '.join(parts)}"
    fix = "No action needed."
    return DoctorCheck(id="config_sources", category="project", code="config.sources.ok", status="ok", message=message, fix=fix)


def project_check(app_path: Path | None, project_root: Path) -> DoctorCheck:
    if app_path and app_path.exists():
        message = f"app.ai found in {app_path.parent}"
        fix = "No action needed."
        status = "ok"
    else:
        message = f"app.ai missing in {project_root}"
        fix = "Create app.ai or pass --app/--project to point at your app."
        status = "warning"
    return DoctorCheck(id="project_file", category="project", code="project.app.missing", status=status, message=message, fix=fix)


def studio_assets_check() -> DoctorCheck:
    base = studio_web_root()
    missing = [fname for fname in STUDIO_ASSETS if not (base / fname).exists()]
    if missing:
        message = f"Studio assets missing: {', '.join(missing)}"
        fix = "Reinstall namel3ss or reinstall the package data."
        status = "error"
    else:
        message = "Studio assets present."
        fix = "No action needed."
        status = "ok"
    return DoctorCheck(id="studio_assets", category="studio", code="studio.assets", status=status, message=message, fix=fix)


def cli_path_check() -> DoctorCheck:
    n3_path = shutil.which("n3") or sys.argv[0]
    message = f"n3 executable resolved to {n3_path} namel3ss {get_version()}"
    fix = "If this is unexpected, ensure your virtualenv/bin is first on PATH."
    return DoctorCheck(id="cli_entrypoint", category="environment", code="cli.entrypoint", status="ok", message=message, fix=fix)


def resolve_target(config: AppConfig | None) -> str:
    if config and config.persistence.target:
        return config.persistence.target.strip().lower()
    env_target = os.getenv("N3_PERSIST_TARGET")
    if env_target:
        return env_target.strip().lower()
    persist_raw = os.getenv("N3_PERSIST")
    if persist_raw and persist_raw.lower() in RESERVED_TRUE_VALUES:
        return "sqlite"
    return "memory"


def _find_shadow_paths(origin: Path | None) -> list[str]:
    shadowed: list[str] = []
    for entry in sys.path:
        if not entry:
            continue
        candidate_root = Path(entry).expanduser().resolve()
        candidate_pkg = candidate_root / "namel3ss"
        if not candidate_pkg.exists():
            continue
        if origin and origin.is_relative_to(candidate_pkg):
            continue
        shadowed.append(str(candidate_pkg))
    return shadowed


def _has_postgres_driver() -> bool:
    return importlib.util.find_spec("psycopg") is not None or importlib.util.find_spec("psycopg2") is not None


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


__all__ = [
    "cli_path_check",
    "config_sources_check",
    "import_path_check",
    "optional_dependencies_check",
    "persistence_check",
    "project_check",
    "python_check",
    "resolve_target",
    "status_icon",
    "studio_assets_check",
]
