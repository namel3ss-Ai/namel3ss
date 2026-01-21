from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Dict, Tuple

from namel3ss.cli.builds import read_latest_build_id
from namel3ss.cli.targets_store import resolve_build_dir
from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.pkg.lockfile import LOCKFILE_FILENAME
from namel3ss.schema.evolution import (
    build_snapshot_path,
    load_schema_snapshot,
    workspace_snapshot_path,
)
from namel3ss.version import get_version


def parse_args(args: list[str]) -> tuple[str | None, str | None]:
    app_arg = None
    target = None
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--target":
            if i + 1 >= len(args):
                raise Namel3ssError(
                    build_guidance_message(
                        what="--target flag is missing a value.",
                        why="A target must be local, service, or edge.",
                        fix="Provide a target after the flag.",
                        example="n3 build --target service",
                    )
                )
            target = args[i + 1]
            i += 2
            continue
        if arg.startswith("--"):
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Unknown flag '{arg}'.",
                    why="Only --target is supported for build.",
                    fix="Remove the unsupported flag.",
                    example="n3 build --target local",
                )
            )
        if app_arg is None:
            app_arg = arg
            i += 1
            continue
        raise Namel3ssError(
            build_guidance_message(
                what="Too many positional arguments.",
                why="Build accepts at most one app path.",
                fix="Provide a single app.ai path or none.",
                example="n3 build app.ai --target service",
            )
        )
    return app_arg, target


def load_previous_schema_snapshot(project_root: Path, target: str) -> dict | None:
    latest_id = read_latest_build_id(project_root, target)
    if latest_id:
        build_path = resolve_build_dir(project_root, target, latest_id)
        if build_path:
            previous_path = build_snapshot_path(build_path)
            snapshot = load_schema_snapshot(previous_path)
            if snapshot:
                return snapshot
    workspace_path = workspace_snapshot_path(project_root)
    return load_schema_snapshot(workspace_path)


def normalize_path(path_value: str | None, project_root: Path | None) -> str | None:
    if path_value is None:
        return None
    if path_value == ":memory:":
        return path_value
    try:
        path = Path(path_value)
    except Exception:
        return str(path_value)
    if not path.is_absolute():
        return path.as_posix()
    if project_root:
        try:
            return path.resolve().relative_to(project_root.resolve()).as_posix()
        except Exception:
            return path.name
    return path.name


def load_lock_snapshot(project_root: Path) -> Tuple[Dict[str, object], str]:
    path = project_root / LOCKFILE_FILENAME
    rel_path = _relative_path(project_root, path)
    if not path.exists():
        return (
            {
                "status": "missing",
                "path": rel_path,
                "hint": "Run `n3 pkg install` to generate namel3ss.lock.json.",
            },
            "missing",
        )
    text = path.read_text(encoding="utf-8")
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    try:
        parsed = json.loads(text)
        snapshot = parsed if isinstance(parsed, dict) else {"raw": parsed}
        return (
            {
                "status": "present",
                "path": rel_path,
                "lockfile": snapshot,
                "digest": digest,
            },
            digest,
        )
    except json.JSONDecodeError as err:
        return (
            {
                "status": "invalid",
                "path": rel_path,
                "error": err.msg,
                "line": err.lineno,
                "column": err.colno,
                "digest": digest,
            },
            digest,
        )


def safe_config_snapshot(config, *, project_root: Path | None = None) -> Dict[str, object]:
    return {
        "persistence": {
            "target": config.persistence.target,
            "db_path": normalize_path(config.persistence.db_path, project_root),
            "database_url": "set" if config.persistence.database_url else None,
            "edge_kv_url": "set" if config.persistence.edge_kv_url else None,
        },
        "identity_defaults": sorted(config.identity.defaults.keys()),
        "providers": {
            "openai_api_key": bool(config.openai.api_key),
            "anthropic_api_key": bool(config.anthropic.api_key),
            "gemini_api_key": bool(config.gemini.api_key),
            "mistral_api_key": bool(config.mistral.api_key),
            "ollama_host": config.ollama.host,
        },
    }


def compute_build_id(
    target: str,
    sources: Dict[Path, str],
    lock_digest: str,
    safe_config: Dict[str, object],
) -> str:
    h = hashlib.sha256()
    h.update(target.encode("utf-8"))
    h.update(get_version().encode("utf-8"))
    for path, text in sorted(sources.items(), key=lambda item: item[0].as_posix()):
        h.update(path.as_posix().encode("utf-8"))
        h.update(text.encode("utf-8"))
    h.update(lock_digest.encode("utf-8"))
    h.update(canonical_json_dumps(safe_config, pretty=False, drop_run_keys=False).encode("utf-8"))
    return f"{target}-{h.hexdigest()[:12]}"


def program_summary(program_ir) -> Dict[str, object]:
    records = sorted(getattr(rec, "name", "") for rec in getattr(program_ir, "records", []) if getattr(rec, "name", ""))
    flows = sorted(flow.name for flow in getattr(program_ir, "flows", []))
    pages = sorted(getattr(page, "name", "") for page in getattr(program_ir, "pages", []) if getattr(page, "name", ""))
    ais = sorted(getattr(program_ir, "ais", {}).keys())
    tools = sorted(getattr(program_ir, "tools", {}).keys())
    agents = sorted(getattr(program_ir, "agents", {}).keys())
    return {
        "records": records,
        "flows": flows,
        "entry_flows": getattr(program_ir, "entry_flows", []),
        "public_flows": getattr(program_ir, "public_flows", []),
        "pages": pages,
        "ai_profiles": ais,
        "tools": tools,
        "agents": agents,
        "theme": getattr(program_ir, "theme", None),
    }


def _relative_path(project_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except Exception:
        return path.name


__all__ = [
    "compute_build_id",
    "load_lock_snapshot",
    "load_previous_schema_snapshot",
    "parse_args",
    "program_summary",
    "safe_config_snapshot",
]
