from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Dict, Tuple

from namel3ss.cli.app_loader import load_program
from namel3ss.cli.app_path import resolve_app_path
from namel3ss.cli.targets import parse_target
from namel3ss.cli.targets_store import (
    BUILD_META_FILENAME,
    build_dir,
    latest_pointer_path,
    write_json,
)
from namel3ss.config.loader import load_config
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.pkg.lockfile import LOCKFILE_FILENAME
from namel3ss.utils.json_tools import dumps_pretty
from namel3ss.version import get_version
from namel3ss.secrets import set_engine_target, set_audit_root


def run_build_command(args: list[str]) -> int:
    app_arg, target_raw = _parse_args(args)
    target = parse_target(target_raw)
    app_path = resolve_app_path(app_arg)
    project_root = app_path.resolve().parent
    set_engine_target(target.name)
    set_audit_root(project_root)
    config = load_config(app_path=app_path)
    program_ir, sources = load_program(app_path.as_posix())
    lock_snapshot, lock_digest = _load_lock_snapshot(project_root)
    safe_config = _safe_config_snapshot(config)
    build_id = _compute_build_id(target.name, sources, lock_digest, safe_config)
    build_path = _prepare_build_dir(project_root, target.name, build_id)
    fingerprints = _write_program_bundle(build_path, project_root, sources)
    program_summary = _program_summary(program_ir)
    write_json(build_path / "program_summary.json", program_summary)
    write_json(build_path / "config.json", safe_config)
    write_json(build_path / "lock_snapshot.json", lock_snapshot)
    metadata = _build_metadata(
        build_id=build_id,
        target=target.name,
        process_model=target.process_model,
        project_root=project_root,
        app_path=app_path,
        safe_config=safe_config,
        program_summary=program_summary,
        lock_digest=lock_digest,
        lock_snapshot=lock_snapshot,
        fingerprints=fingerprints,
        recommended_persistence=target.persistence_default,
    )
    write_json(build_path / BUILD_META_FILENAME, metadata)
    write_json(
        latest_pointer_path(project_root, target.name),
        {"build_id": build_id, "target": target.name},
    )
    if target.name == "service":
        _write_service_bundle(build_path, build_id)
    if target.name == "edge":
        _write_edge_stub(build_path)
    print(f"Build ready: {build_path.as_posix()}")
    print(f"Target: {target.name} • Build ID: {build_id}")
    return 0


def _parse_args(args: list[str]) -> tuple[str | None, str | None]:
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


def _prepare_build_dir(project_root: Path, target: str, build_id: str) -> Path:
    path = build_dir(project_root, target, build_id)
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write_program_bundle(build_path: Path, project_root: Path, sources: Dict[Path, str]) -> list[dict]:
    program_root = build_path / "program"
    program_root.mkdir(parents=True, exist_ok=True)
    fingerprints = []
    for src_path, text in sorted(sources.items(), key=lambda item: item[0].as_posix()):
        try:
            rel = src_path.resolve().relative_to(project_root.resolve())
        except ValueError:
            rel = Path(src_path.name)
        dest = program_root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text, encoding="utf-8")
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        fingerprints.append({"path": rel.as_posix(), "sha256": digest})
    return sorted(fingerprints, key=lambda item: item["path"])


def _program_summary(program_ir) -> Dict[str, object]:
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


def _load_lock_snapshot(project_root: Path) -> Tuple[Dict[str, object], str]:
    path = project_root / LOCKFILE_FILENAME
    if not path.exists():
        return (
            {
                "status": "missing",
                "path": path.as_posix(),
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
                "path": path.as_posix(),
                "lockfile": snapshot,
                "digest": digest,
            },
            digest,
        )
    except json.JSONDecodeError as err:
        return (
            {
                "status": "invalid",
                "path": path.as_posix(),
                "error": err.msg,
                "line": err.lineno,
                "column": err.colno,
                "digest": digest,
            },
            digest,
        )


def _safe_config_snapshot(config) -> Dict[str, object]:
    return {
        "persistence": {
            "target": config.persistence.target,
            "db_path": config.persistence.db_path,
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


def _compute_build_id(
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
    h.update(dumps_pretty(safe_config).encode("utf-8"))
    return f"{target}-{h.hexdigest()[:12]}"


def _build_metadata(
    *,
    build_id: str,
    target: str,
    process_model: str,
    project_root: Path,
    app_path: Path,
    safe_config: Dict[str, object],
    program_summary: Dict[str, object],
    lock_digest: str,
    lock_snapshot: Dict[str, object],
    fingerprints: list[dict],
    recommended_persistence: str,
) -> Dict[str, object]:
    try:
        app_rel = app_path.resolve().relative_to(project_root.resolve())
    except ValueError:
        app_rel = Path(app_path.name)
    return {
        "build_id": build_id,
        "target": target,
        "process_model": process_model,
        "project_root": project_root.as_posix(),
        "app_path": app_path.as_posix(),
        "app_relative_path": app_rel.as_posix(),
        "namel3ss_version": get_version(),
        "persistence_target": safe_config.get("persistence", {}).get("target"),
        "recommended_persistence": recommended_persistence,
        "lockfile_digest": lock_digest,
        "lockfile_status": lock_snapshot.get("status"),
        "program_summary": program_summary,
        "source_fingerprints": fingerprints,
    }


def _write_service_bundle(build_path: Path, build_id: str) -> None:
    bundle_root = build_path / "service"
    bundle_root.mkdir(parents=True, exist_ok=True)
    instructions = "\n".join(
        [
            "namel3ss service bundle",
            f"Build: {build_id}",
            "",
            "Run the promoted build locally:",
            f"  n3 run --target service --build {build_id}",
            "",
            "Health endpoint (default port 8787):",
            "  GET http://127.0.0.1:8787/health",
        ]
    )
    (bundle_root / "README.txt").write_text(instructions.strip() + "\n", encoding="utf-8")


def _write_edge_stub(build_path: Path) -> None:
    stub_root = build_path / "edge"
    stub_root.mkdir(parents=True, exist_ok=True)
    note = "\n".join(
        [
            "Edge simulator bundle (stub)",
            "This alpha release records the build inputs but does not generate a runnable edge package yet.",
            "Next steps: run `n3 run --target edge` to simulate the target locally.",
        ]
    )
    (stub_root / "README.txt").write_text(note.strip() + "\n", encoding="utf-8")


__all__ = ["run_build_command"]
