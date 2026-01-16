from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Dict, Tuple

from namel3ss.cli.app_loader import load_program
from namel3ss.cli.app_path import resolve_app_path
from namel3ss.cli.builds import read_latest_build_id
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
from namel3ss.determinism import canonical_json_dumps
from namel3ss.media import MediaValidationMode
from namel3ss.pkg.lockfile import LOCKFILE_FILENAME
from namel3ss.resources import package_root, studio_web_root
from namel3ss.schema.evolution import (
    build_schema_snapshot,
    build_snapshot_path,
    enforce_schema_compatibility,
    load_schema_snapshot,
    workspace_snapshot_path,
)
from namel3ss.validation import ValidationWarning
from namel3ss.validation_entrypoint import build_static_manifest
from namel3ss.version import get_version
from namel3ss.secrets import set_engine_target, set_audit_root
from namel3ss.ui.export.actions import build_actions_export
from namel3ss.ui.export.schema import build_schema_export
from namel3ss.ui.export.ui import build_ui_export

MANIFEST_FILENAME = "manifest.json"
UI_DIRNAME = "ui"
WEB_DIRNAME = "web"
BUILD_REPORT_JSON = "build_report.json"
BUILD_REPORT_TEXT = "build_report.txt"
PROD_HTML_FILENAME = "prod.html"
RUNTIME_WEB_ASSETS = ("runtime.css", "runtime.js")
STUDIO_WEB_ASSETS = (
    "studio_ui.css",
    "theme_tokens.css",
    "theme_tokens.js",
    "theme_runtime.js",
    "ui_renderer.js",
    "ui_renderer_chart.js",
    "ui_renderer_chat.js",
    "ui_renderer_collections.js",
    "ui_renderer_form.js",
)


def run_build_command(args: list[str]) -> int:
    app_arg, target_raw = _parse_args(args)
    target = parse_target(target_raw)
    app_path = resolve_app_path(app_arg)
    project_root = app_path.resolve().parent
    set_engine_target(target.name)
    set_audit_root(project_root)
    config = load_config(app_path=app_path)
    program_ir, sources = load_program(app_path.as_posix())
    schema_snapshot = build_schema_snapshot(getattr(program_ir, "records", []))
    previous_snapshot = _load_previous_schema_snapshot(project_root, target.name)
    enforce_schema_compatibility(
        getattr(program_ir, "records", []),
        previous_snapshot=previous_snapshot,
        context="build",
    )
    warnings: list[ValidationWarning] = []
    manifest = build_static_manifest(
        program_ir,
        config=config,
        state={},
        store=None,
        warnings=warnings,
        media_mode=MediaValidationMode.BUILD,
    )
    lock_snapshot, lock_digest = _load_lock_snapshot(project_root)
    safe_config = _safe_config_snapshot(config, project_root=project_root)
    build_id = _compute_build_id(target.name, sources, lock_digest, safe_config)
    build_path = _prepare_build_dir(project_root, target.name, build_id)
    fingerprints = _write_program_bundle(build_path, project_root, sources)
    program_summary = _program_summary(program_ir)
    write_json(build_path / "program_summary.json", program_summary)
    write_json(build_path / "config.json", safe_config)
    write_json(build_path / "lock_snapshot.json", lock_snapshot)
    artifacts = {
        "program": "program",
        "config": "config.json",
        "lock_snapshot": "lock_snapshot.json",
        "program_summary": "program_summary.json",
        "build_report_json": BUILD_REPORT_JSON,
        "build_report_text": BUILD_REPORT_TEXT,
    }
    artifacts["manifest"] = _write_manifest(build_path, manifest)
    artifacts["schema_snapshot"] = _write_schema_snapshot(build_path, schema_snapshot)
    artifacts["ui"] = _write_ui_contract(build_path, program_ir, manifest)
    artifacts["web"] = _write_web_bundle(build_path)
    report_payload, report_text = _build_report(
        build_id=build_id,
        target=target.name,
        program_summary=program_summary,
        artifacts=artifacts,
        warnings=warnings,
    )
    _write_build_report(build_path, report_payload, report_text)
    app_relative_path = _relative_path(project_root, app_path)
    metadata = _build_metadata(
        build_id=build_id,
        target=target.name,
        process_model=target.process_model,
        safe_config=safe_config,
        program_summary=program_summary,
        lock_digest=lock_digest,
        lock_snapshot=lock_snapshot,
        fingerprints=fingerprints,
        recommended_persistence=target.persistence_default,
        app_relative_path=app_relative_path,
        artifacts=artifacts,
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


def _relative_path(project_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except Exception:
        return path.name


def _load_previous_schema_snapshot(project_root: Path, target: str) -> dict | None:
    latest_id = read_latest_build_id(project_root, target)
    if latest_id:
        previous_path = build_snapshot_path(build_dir(project_root, target, latest_id))
        snapshot = load_schema_snapshot(previous_path)
        if snapshot:
            return snapshot
    workspace_path = workspace_snapshot_path(project_root)
    return load_schema_snapshot(workspace_path)


def _normalize_path(path_value: str | None, project_root: Path | None) -> str | None:
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


def _load_lock_snapshot(project_root: Path) -> Tuple[Dict[str, object], str]:
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


def _safe_config_snapshot(config, *, project_root: Path | None = None) -> Dict[str, object]:
    return {
        "persistence": {
            "target": config.persistence.target,
            "db_path": _normalize_path(config.persistence.db_path, project_root),
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
    h.update(canonical_json_dumps(safe_config, pretty=False, drop_run_keys=False).encode("utf-8"))
    return f"{target}-{h.hexdigest()[:12]}"


def _build_metadata(
    *,
    build_id: str,
    target: str,
    process_model: str,
    safe_config: Dict[str, object],
    program_summary: Dict[str, object],
    lock_digest: str,
    lock_snapshot: Dict[str, object],
    fingerprints: list[dict],
    recommended_persistence: str,
    app_relative_path: str,
    artifacts: dict,
) -> Dict[str, object]:
    return {
        "build_id": build_id,
        "target": target,
        "process_model": process_model,
        "app_relative_path": app_relative_path,
        "namel3ss_version": get_version(),
        "persistence_target": safe_config.get("persistence", {}).get("target"),
        "recommended_persistence": recommended_persistence,
        "lockfile_digest": lock_digest,
        "lockfile_status": lock_snapshot.get("status"),
        "program_summary": program_summary,
        "source_fingerprints": fingerprints,
        "artifacts": artifacts,
    }


def _write_manifest(build_path: Path, manifest: dict) -> str:
    path = build_path / MANIFEST_FILENAME
    payload = manifest if isinstance(manifest, dict) else {}
    write_json(path, payload)
    return MANIFEST_FILENAME


def _write_schema_snapshot(build_path: Path, snapshot: dict) -> str:
    path = build_snapshot_path(build_path)
    write_json(path, snapshot)
    return path.relative_to(build_path).as_posix()


def _write_ui_contract(build_path: Path, program_ir, manifest: dict) -> dict:
    ui_dir = build_path / UI_DIRNAME
    ui_dir.mkdir(parents=True, exist_ok=True)
    ui_export = build_ui_export(manifest)
    actions_export = build_actions_export(manifest)
    schema_export = build_schema_export(program_ir, manifest)
    write_json(ui_dir / "ui.json", ui_export)
    write_json(ui_dir / "actions.json", actions_export)
    write_json(ui_dir / "schema.json", schema_export)
    return {
        "ui": f"{UI_DIRNAME}/ui.json",
        "actions": f"{UI_DIRNAME}/actions.json",
        "schema": f"{UI_DIRNAME}/schema.json",
    }


def _write_web_bundle(build_path: Path) -> str:
    web_root = build_path / WEB_DIRNAME
    web_root.mkdir(parents=True, exist_ok=True)
    runtime_root = _runtime_web_root()
    prod_src = runtime_root / PROD_HTML_FILENAME
    _copy_asset(prod_src, web_root / "index.html")
    for name in RUNTIME_WEB_ASSETS:
        _copy_asset(runtime_root / name, web_root / name)
    studio_root = studio_web_root()
    for name in STUDIO_WEB_ASSETS:
        _copy_asset(studio_root / name, web_root / name)
    return WEB_DIRNAME


def _copy_asset(src: Path, dest: Path) -> None:
    if not src.exists():
        raise Namel3ssError(
            build_guidance_message(
                what=f"Missing runtime asset: {src.name}.",
                why="Build could not copy required runtime assets.",
                fix="Reinstall namel3ss or re-run the build after restoring assets.",
                example="n3 build --target service",
            )
        )
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(src.read_bytes())


def _runtime_web_root() -> Path:
    return package_root() / "runtime" / "web"


def _build_report(
    *,
    build_id: str,
    target: str,
    program_summary: dict,
    artifacts: dict,
    warnings: list[ValidationWarning],
) -> tuple[dict, str]:
    warning_payloads = _normalize_warnings(warnings)
    payload = {
        "schema_version": 1,
        "build_id": build_id,
        "target": target,
        "program_summary": program_summary,
        "artifacts": artifacts,
        "warning_count": len(warning_payloads),
        "warnings": warning_payloads,
    }
    text = _render_build_report(payload)
    return payload, text


def _normalize_warnings(warnings: list[ValidationWarning]) -> list[dict]:
    payloads = [warning.to_dict() for warning in warnings if isinstance(warning, ValidationWarning)]
    return sorted(
        payloads,
        key=lambda item: (
            str(item.get("code") or ""),
            str(item.get("message") or ""),
            str(item.get("path") or ""),
            int(item.get("line") or 0),
            int(item.get("column") or 0),
        ),
    )


def _render_build_report(payload: dict) -> str:
    lines = [
        "Build report",
        "",
        "Build",
        f"- id: {payload.get('build_id')}",
        f"- target: {payload.get('target')}",
        "",
        "Artifacts",
    ]
    artifacts = payload.get("artifacts") if isinstance(payload.get("artifacts"), dict) else {}
    manifest_path = artifacts.get("manifest")
    if manifest_path:
        lines.append(f"- manifest: {manifest_path}")
    ui_paths = artifacts.get("ui") if isinstance(artifacts.get("ui"), dict) else {}
    if ui_paths:
        ui_entries = [ui_paths.get("ui"), ui_paths.get("actions"), ui_paths.get("schema")]
        ui_entries = [entry for entry in ui_entries if entry]
        lines.append(f"- ui contract: {', '.join(ui_entries)}")
    for key in ("program", "config", "lock_snapshot", "program_summary", "web"):
        value = artifacts.get(key)
        if value:
            lines.append(f"- {key.replace('_', ' ')}: {value}")
    for key in ("build_report_json", "build_report_text"):
        value = artifacts.get(key)
        if value:
            label = "report json" if key == "build_report_json" else "report text"
            lines.append(f"- {label}: {value}")
    lines.append("")
    lines.append("Warnings")
    warnings = payload.get("warnings") if isinstance(payload.get("warnings"), list) else []
    if not warnings:
        lines.append("- none")
    else:
        for warning in warnings:
            if not isinstance(warning, dict):
                continue
            code = warning.get("code") or "warning"
            message = warning.get("message") or ""
            entry = f"- {code}: {message}".rstrip(": ")
            fix = warning.get("fix")
            if fix:
                entry = f"{entry} (fix: {fix})"
            lines.append(entry)
    return "\n".join(lines).rstrip() + "\n"


def _write_build_report(build_path: Path, payload: dict, text: str) -> None:
    write_json(build_path / BUILD_REPORT_JSON, payload)
    (build_path / BUILD_REPORT_TEXT).write_text(text, encoding="utf-8")


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
