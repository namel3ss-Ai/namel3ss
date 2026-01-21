from __future__ import annotations

from pathlib import Path

from namel3ss.cli.app_loader import load_program
from namel3ss.cli.app_path import default_missing_app_message, resolve_app_path
from namel3ss.cli.build_mode import artifacts, reports, validate
from namel3ss.cli.targets import parse_target
from namel3ss.cli.targets_store import BUILD_META_FILENAME, latest_pointer_path, write_json
from namel3ss.config.loader import load_config
from namel3ss.media import MediaValidationMode
from namel3ss.schema.evolution import build_schema_snapshot, enforce_schema_compatibility
from namel3ss.validation import ValidationWarning
from namel3ss.validation_entrypoint import build_static_manifest
from namel3ss.secrets import set_audit_root, set_engine_target


def run_build_command(args: list[str]) -> int:
    app_arg, target_raw = validate.parse_args(args)
    target = parse_target(target_raw)
    app_path = resolve_app_path(
        app_arg,
        search_parents=False,
        missing_message=default_missing_app_message("build"),
    )
    project_root = app_path.resolve().parent
    set_engine_target(target.name)
    set_audit_root(project_root)
    config = load_config(app_path=app_path)
    program_ir, sources = load_program(app_path.as_posix())
    schema_snapshot = build_schema_snapshot(getattr(program_ir, "records", []))
    previous_snapshot = validate.load_previous_schema_snapshot(project_root, target.name)
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
    lock_snapshot, lock_digest = validate.load_lock_snapshot(project_root)
    safe_config = validate.safe_config_snapshot(config, project_root=project_root)
    build_id = validate.compute_build_id(target.name, sources, lock_digest, safe_config)
    build_path = artifacts.prepare_build_dir(project_root, target.name, build_id)
    fingerprints = artifacts.write_program_bundle(build_path, project_root, sources)
    program_summary = validate.program_summary(program_ir)
    write_json(build_path / "program_summary.json", program_summary)
    write_json(build_path / "config.json", safe_config)
    write_json(build_path / "lock_snapshot.json", lock_snapshot)
    entry_instructions = artifacts.build_entry_instructions(target.name, build_id)
    artifacts_map = {
        "program": "program",
        "config": "config.json",
        "lock_snapshot": "lock_snapshot.json",
        "program_summary": "program_summary.json",
        "build_report_json": reports.BUILD_REPORT_JSON,
        "build_report_text": reports.BUILD_REPORT_TEXT,
    }
    artifacts_map["manifest"] = artifacts.write_manifest(build_path, manifest)
    artifacts_map["schema_snapshot"] = artifacts.write_schema_snapshot(build_path, schema_snapshot)
    artifacts_map["ui"] = artifacts.write_ui_contract(build_path, program_ir, manifest)
    artifacts_map["web"] = artifacts.write_web_bundle(build_path)
    artifacts_map["entry_instructions"] = artifacts.write_entry_instructions(build_path, entry_instructions)
    report_payload, report_text = reports.build_report(
        build_id=build_id,
        target=target.name,
        program_summary=program_summary,
        artifacts=artifacts_map,
        warnings=warnings,
    )
    reports.write_build_report(build_path, report_payload, report_text)
    app_relative_path = _relative_path(project_root, app_path)
    metadata = artifacts.build_metadata(
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
        artifacts=artifacts_map,
        entry_instructions=entry_instructions,
    )
    write_json(build_path / BUILD_META_FILENAME, metadata)
    write_json(
        latest_pointer_path(project_root, target.name),
        {"build_id": build_id, "target": target.name},
    )
    if target.name == "service":
        artifacts.write_service_bundle(build_path, build_id)
    if target.name == "edge":
        artifacts.write_edge_stub(build_path, build_id)
    print(f"Build ready: {_relative_path(project_root, build_path)}")
    print(f"Target: {target.name} • Build ID: {build_id}")
    return 0


def _relative_path(project_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except Exception:
        return path.name


__all__ = ["run_build_command"]
