from __future__ import annotations

import importlib.util
import json
import os
import platform
import shutil
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List
from urllib.parse import urlsplit, urlunsplit

from namel3ss.config.loader import resolve_config, ConfigSource
from namel3ss.config.model import AppConfig
from namel3ss.version import get_version
MIN_PYTHON = (3, 10)
SUPPORTED_PYTHON_RANGE = ">=3.10"
PROVIDER_ENV_VARS = [
    "NAMEL3SS_OPENAI_API_KEY",
    "NAMEL3SS_OPENAI_BASE_URL",
    "NAMEL3SS_ANTHROPIC_API_KEY",
    "NAMEL3SS_GEMINI_API_KEY",
    "NAMEL3SS_MISTRAL_API_KEY",
    "NAMEL3SS_OLLAMA_HOST",
    "NAMEL3SS_OLLAMA_TIMEOUT_SECONDS",
]
STUDIO_ASSETS = ["index.html", "app.js", "styles.css"]
STATUS_ICONS = {"ok": "✅", "warning": "⚠️", "error": "❌"}
RESERVED_TRUE_VALUES = {"1", "true", "yes", "on"}
SUPPORTED_TARGETS = {"memory", "sqlite", "postgres", "edge"}


@dataclass
class DoctorCheck:
    id: str
    status: str
    message: str
    fix: str


def _status_icon(status: str) -> str:
    return STATUS_ICONS.get(status, "⚠️")


def _python_check() -> DoctorCheck:
    version_tuple = sys.version_info[:3]
    version_str = ".".join(map(str, version_tuple))
    supported = version_tuple >= MIN_PYTHON
    status = "ok" if supported else "error"
    message = f"Python {version_str} (requires {SUPPORTED_PYTHON_RANGE})"
    fix = "Install Python 3.10+ and re-run `pip install namel3ss`."
    return DoctorCheck(id="python_version", status=status, message=message, fix=fix)


def _find_shadow_paths(origin: Path | None) -> List[str]:
    shadowed: List[str] = []
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


def _import_path_check() -> DoctorCheck:
    spec = importlib.util.find_spec("namel3ss")
    origin = Path(spec.origin).resolve() if spec and spec.origin else None
    pythonpath = os.getenv("PYTHONPATH") or ""
    shadowed = _find_shadow_paths(origin)
    if shadowed:
        message = f"namel3ss import may be shadowed (using {origin}, also found {', '.join(shadowed)})"
        fix = "Clear PYTHONPATH or remove extra namel3ss copies so the installed CLI is used."
        return DoctorCheck(id="import_path", status="warning", message=message, fix=fix)
    if pythonpath:
        message = f"PYTHONPATH is set; current namel3ss import is {origin}"
        fix = "Unset PYTHONPATH or activate a clean virtualenv before running `n3`."
        return DoctorCheck(id="import_path", status="warning", message=message, fix=fix)
    message = f"namel3ss import path: {origin}"
    fix = "No action needed."
    return DoctorCheck(id="import_path", status="ok", message=message, fix=fix)


def _optional_dependencies_check(config: AppConfig | None) -> DoctorCheck:
    target = _resolve_target(config)
    if target == "postgres" and not _has_postgres_driver():
        message = "Postgres driver missing (psycopg not installed)."
        fix = 'Install the postgres extra: pip install "namel3ss[postgres]".'
        return DoctorCheck(id="optional_dependencies", status="error", message=message, fix=fix)
    message = "Optional dependencies: install psycopg only if you use Postgres."
    fix = "No action needed."
    return DoctorCheck(id="optional_dependencies", status="ok", message=message, fix=fix)


def _provider_env_check() -> DoctorCheck:
    missing = [name for name in PROVIDER_ENV_VARS if not os.getenv(name)]
    if missing:
        message = f"AI provider keys missing: {', '.join(missing)}"
        fix = "Export the keys you plan to use (e.g., NAMEL3SS_OPENAI_API_KEY) or ignore if not needed."
        status = "warning"
    else:
        message = "AI provider keys detected."
        fix = "No action needed."
        status = "ok"
    return DoctorCheck(id="provider_envs", status=status, message=message, fix=fix)


def _persistence_check(config: AppConfig | None) -> DoctorCheck:
    target = _resolve_target(config)
    if target not in SUPPORTED_TARGETS:
        message = f"Persistence target '{target}' is not supported."
        fix = "Set N3_PERSIST_TARGET to sqlite, postgres, edge, or memory."
        return DoctorCheck(id="persistence", status="error", message=message, fix=fix)
    if target == "memory":
        message = "Persistence disabled (memory store)."
        fix = "Set N3_PERSIST_TARGET=sqlite to persist to .namel3ss/data.db."
        return DoctorCheck(id="persistence", status="warning", message=message, fix=fix)
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
        return DoctorCheck(id="persistence", status=status, message=message, fix=fix)
    if target == "postgres":
        url = config.persistence.database_url if config else os.getenv("N3_DATABASE_URL")
        if not url:
            message = "Persistence target postgres but N3_DATABASE_URL is missing."
            fix = "Set N3_DATABASE_URL to a valid postgres:// URL."
            return DoctorCheck(id="persistence", status="error", message=message, fix=fix)
        redacted = _redact_url(url)
        message = f"Persistence target postgres with N3_DATABASE_URL set ({redacted})."
        fix = "No action needed."
        return DoctorCheck(id="persistence", status="ok", message=message, fix=fix)
    if target == "edge":
        url = config.persistence.edge_kv_url if config else os.getenv("N3_EDGE_KV_URL")
        if not url:
            message = "Persistence target edge but N3_EDGE_KV_URL is missing."
            fix = "Set N3_EDGE_KV_URL or switch to sqlite/postgres."
            return DoctorCheck(id="persistence", status="error", message=message, fix=fix)
        redacted = _redact_url(url)
        message = f"Persistence target edge configured ({redacted})."
        fix = "Use sqlite/postgres unless you are testing edge integrations."
        return DoctorCheck(id="persistence", status="warning", message=message, fix=fix)
    return DoctorCheck(id="persistence", status="warning", message="Persistence target unknown.", fix="Check N3_PERSIST_TARGET.")


def _config_sources_check(sources: list[ConfigSource]) -> DoctorCheck:
    if not sources:
        message = "Config sources: defaults only (no env/.env/namel3ss.toml)."
        fix = "Add .env or namel3ss.toml for defaults, or set environment variables."
        return DoctorCheck(id="config_sources", status="warning", message=message, fix=fix)
    parts = []
    for source in sources:
        if source.kind == "env":
            parts.append("env")
        elif source.path:
            parts.append(f"{source.kind} ({source.path})")
        else:
            parts.append(source.kind)
    message = f"Config sources: {', '.join(parts)}"
    fix = "No action needed."
    return DoctorCheck(id="config_sources", status="ok", message=message, fix=fix)


def _load_config_sources() -> tuple[DoctorCheck | None, list[ConfigSource], AppConfig | None]:
    root = Path.cwd()
    app_path = root / "app.ai"
    try:
        if app_path.exists():
            config, sources = resolve_config(app_path=app_path, root=root)
        else:
            config, sources = resolve_config(root=root)
    except Exception as err:
        details = str(err).splitlines()[0]
        message = f"Config sources failed to load: {details}"
        fix = "Check namel3ss.toml and environment variables."
        return DoctorCheck(id="config_sources", status="error", message=message, fix=fix), [], None
    return None, sources, config


def _resolve_target(config: AppConfig | None) -> str:
    if config and config.persistence.target:
        return config.persistence.target.strip().lower()
    env_target = os.getenv("N3_PERSIST_TARGET")
    if env_target:
        return env_target.strip().lower()
    persist_raw = os.getenv("N3_PERSIST")
    if persist_raw and persist_raw.lower() in RESERVED_TRUE_VALUES:
        return "sqlite"
    return "memory"


def _has_postgres_driver() -> bool:
    return (
        importlib.util.find_spec("psycopg") is not None
        or importlib.util.find_spec("psycopg2") is not None
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


def _project_check() -> DoctorCheck:
    app_path = Path.cwd() / "app.ai"
    if app_path.exists():
        message = f"app.ai found in {Path.cwd()}"
        fix = "No action needed."
        status = "ok"
    else:
        message = f"app.ai missing in {Path.cwd()}"
        fix = "Create or point `n3` at your .ai file (e.g., `n3 examples/demo_crud_dashboard.ai check`)."
        status = "warning"
    return DoctorCheck(id="project_file", status=status, message=message, fix=fix)


def _studio_assets_check() -> DoctorCheck:
    base = Path(__file__).resolve().parent.parent / "studio" / "web"
    missing = [fname for fname in STUDIO_ASSETS if not (base / fname).exists()]
    if missing:
        message = f"Studio assets missing: {', '.join(missing)}"
        fix = "Reinstall namel3ss or reinstall the package data."
        status = "error"
    else:
        message = "Studio assets present."
        fix = "No action needed."
        status = "ok"
    return DoctorCheck(id="studio_assets", status=status, message=message, fix=fix)


def _cli_path_check() -> DoctorCheck:
    n3_path = shutil.which("n3") or sys.argv[0]
    message = f"n3 executable resolved to {n3_path} (namel3ss {get_version()})"
    fix = "If this is unexpected, ensure your virtualenv/bin is first on PATH."
    return DoctorCheck(id="cli_entrypoint", status="ok", message=message, fix=fix)


def _overall_status(checks: Iterable[DoctorCheck]) -> str:
    statuses = {c.status for c in checks}
    if "error" in statuses:
        return "error"
    if "warning" in statuses:
        return "warning"
    return "ok"


def build_report() -> Dict[str, Any]:
    config_check, config_sources, config = _load_config_sources()
    checks: List[DoctorCheck] = [
        _python_check(),
        _import_path_check(),
        _optional_dependencies_check(config),
        _provider_env_check(),
        config_check or _config_sources_check(config_sources),
        _persistence_check(config),
        _project_check(),
        _studio_assets_check(),
        _cli_path_check(),
    ]
    return {"status": _overall_status(checks), "checks": [asdict(c) for c in checks]}


def _print_human(report: Dict[str, Any]) -> None:
    groups = {
        "Environment": {"python_version", "import_path", "optional_dependencies"},
        "Project": {"project_file", "config_sources", "persistence", "cli_entrypoint"},
        "AI providers": {"provider_envs"},
        "Studio": {"studio_assets"},
    }
    checks_by_id = {c["id"]: c for c in report["checks"]}
    for title, ids in groups.items():
        print(f"{title}:")
        for cid in ids:
            check = checks_by_id.get(cid)
            if not check:
                continue
            icon = _status_icon(check["status"])
            print(f"  {icon} {check['message']}")
            if check["fix"]:
                print(f"      Fix: {check['fix']}")


def _print_failure(exc: Exception, json_mode: bool) -> None:
    message = "n3 doctor failed to run. Please report this with the stack trace."
    fix = "Re-run with a clean environment or reinstall namel3ss."
    payload = {
        "status": "error",
        "checks": [
            {"id": "doctor", "status": "error", "message": message, "fix": fix, "error": str(exc)}
        ],
    }
    if json_mode:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"❌ {message}")
        print(f"      Fix: {fix}")
        print(f"      Details: {exc}")


def run_doctor(json_mode: bool = False) -> int:
    try:
        report = build_report()
        if json_mode:
            print(json.dumps(report, indent=2, sort_keys=True))
        else:
            _print_human(report)
        return 0
    except Exception as exc:  # pragma: no cover - defensive guard rail
        _print_failure(exc, json_mode)
        return 1
