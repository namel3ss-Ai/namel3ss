from __future__ import annotations

import os
from pathlib import Path

from namel3ss.cli.app_loader import load_program
from namel3ss.cli.app_path import resolve_app_path
from namel3ss.cli.builds import app_path_from_metadata, load_build_metadata, read_latest_build_id
from namel3ss.cli.proofs import record_active_proof, record_proof_rollback, write_proof
from namel3ss.cli.promotion_state import load_state, record_promotion, record_rollback
from namel3ss.cli.targets import parse_target
from namel3ss.cli.targets_store import write_json
from namel3ss.config.loader import load_config
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.governance.verify import run_verify
from namel3ss.proofs import build_engine_proof
from namel3ss.runtime.data.migration_runner import apply_plan, status_payload
from namel3ss.runtime.data.migration_store import load_state as load_migration_state
from namel3ss.runtime.storage.factory import create_store
from namel3ss.secrets import set_audit_root, set_engine_target


def run_promote_command(args: list[str]) -> int:
    app_arg, target_raw, build_id, rollback, with_migrations = _parse_args(args)
    project_root = resolve_app_path(app_arg).parent
    set_engine_target(target_raw or "local")
    set_audit_root(project_root)
    if rollback:
        _perform_rollback(project_root)
        return 0
    if target_raw is None:
        raise Namel3ssError(
            build_guidance_message(
                what="Missing target for promotion.",
                why="Use --to to pick local, service, or edge.",
                fix="Pass a target to promote to.",
                example="n3 ship --to service",
            )
        )
    target = parse_target(target_raw)
    selected_build = build_id or read_latest_build_id(project_root, target.name)
    if not selected_build:
        raise Namel3ssError(
            build_guidance_message(
                what=f"No build found for target '{target.name}'.",
                why="Promotion needs a build snapshot.",
                fix="Run `n3 pack` for the target, then ship again.",
                example="n3 pack --target service",
            )
        )
    build_path, metadata = load_build_metadata(project_root, target.name, selected_build)
    meta_target = str(metadata.get("target", target.name))
    if meta_target != target.name:
        raise Namel3ssError(
            build_guidance_message(
                what=f"Build '{selected_build}' was created for target '{meta_target}'.",
                why="Targets cannot be mixed during promotion.",
                fix="Build a snapshot for the requested target.",
                example=f"n3 pack --target {target.name}",
            )
        )
    app_snapshot = app_path_from_metadata(build_path, metadata)
    lock_snapshot = _load_build_lock_snapshot(build_path)
    _maybe_verify_on_ship(app_snapshot, project_root, target.name)
    _maybe_handle_migrations(app_snapshot, project_root, with_migrations=with_migrations)
    proof_id, proof = build_engine_proof(
        app_snapshot,
        target=target.name,
        build_id=selected_build,
        lock_snapshot_override=lock_snapshot,
    )
    proof_path = write_proof(project_root, proof_id, proof)
    record_promotion(project_root, target.name, selected_build)
    record_active_proof(project_root, proof_id, target.name, selected_build)
    print(f"Promoted build {selected_build} to target '{target.name}'.")
    print(f"Snapshot: {app_snapshot.parent.as_posix()}")
    print(f"Engine proof: {proof_id}")
    print(f"Proof stored: {proof_path.as_posix()}")
    if target.name == "service":
        print("Next: n3 run --target service --build {id}".format(id=selected_build))
    if target.name == "edge":
        print("Edge engine is simulated; run `n3 run --target edge` for the stub.")
    print("Note: database migrations are not auto-rolled back in this phase.")
    return 0


def _perform_rollback(project_root: Path) -> None:
    state = load_state(project_root)
    active = state.get("active") or {}
    prev = state.get("previous") or {}
    if not prev.get("target") and not active.get("target"):
        raise Namel3ssError(
            build_guidance_message(
                what="Nothing to roll back.",
                why="No previous promotion is recorded.",
                fix="Promote a build before rolling back.",
                example="n3 ship --to local",
            )
        )
    new_state = record_rollback(project_root)
    record_proof_rollback(project_root)
    active_after = new_state.get("active") or {}
    target = active_after.get("target") or "none"
    build = active_after.get("build_id") or "none"
    print(f"Rolled back. Active target: {target}. Active build: {build}.")
    print("Database schema changes are not automatically rolled back.")


def _maybe_verify_on_ship(app_snapshot: Path, project_root: Path, target: str) -> None:
    enabled = os.getenv("N3_VERIFY_ON_SHIP", "").strip().lower() in {"1", "true", "yes", "on"}
    if not enabled:
        return
    report = run_verify(
        app_snapshot,
        target=target,
        prod=True,
        config_root=project_root,
        project_root_override=project_root,
    )
    write_json(project_root / ".namel3ss" / "verify.json", report)
    if report.get("status") != "ok":
        raise Namel3ssError(
            build_guidance_message(
                what="Verify failed for promotion.",
                why="One or more governance checks failed.",
                fix="Run `n3 verify --prod` and address the failures before shipping.",
                example="n3 verify --prod --json",
            )
        )


def _load_build_lock_snapshot(build_path: Path) -> dict | None:
    path = build_path / "lock_snapshot.json"
    if not path.exists():
        return None
    try:
        import json

        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def _parse_args(args: list[str]) -> tuple[str | None, str | None, str | None, bool, bool]:
    app_arg = None
    target = None
    build_id = None
    rollback = False
    with_migrations = False
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--to":
            if i + 1 >= len(args):
                raise Namel3ssError(
                    build_guidance_message(
                        what="--to flag is missing a value.",
                        why="Promotion requires a target.",
                        fix="Pass local, service, or edge after --to.",
                        example="n3 ship --to service",
                    )
                )
            target = args[i + 1]
            i += 2
            continue
        if arg == "--build":
            if i + 1 >= len(args):
                raise Namel3ssError(
                    build_guidance_message(
                        what="--build flag is missing a value.",
                        why="A build id must follow --build.",
                        fix="Provide the build id.",
                        example="n3 ship --to service --build service-abc123",
                    )
                )
            build_id = args[i + 1]
            i += 2
            continue
        if arg == "--with-migrations":
            with_migrations = True
            i += 1
            continue
        if arg in {"--rollback", "--back"}:
            rollback = True
            i += 1
            continue
        if arg.startswith("--"):
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Unknown flag '{arg}'.",
                    why="Only --to, --build, --rollback, and --with-migrations are supported.",
                    fix="Remove the unsupported flag.",
                    example="n3 ship --to local",
                )
            )
        if app_arg is None:
            app_arg = arg
            i += 1
            continue
        raise Namel3ssError(
            build_guidance_message(
                what="Too many positional arguments.",
                why="Promotion accepts at most one app path.",
                fix="Provide a single app.ai path or none.",
                example="n3 ship app.ai --to service",
            )
        )
    if rollback and (target or build_id):
        raise Namel3ssError(
            build_guidance_message(
                what="Rollback cannot be combined with other flags.",
                why="Rollback reverts the last promotion only.",
                fix="Run rollback alone.",
                example="n3 ship --back",
            )
        )
    if rollback and with_migrations:
        raise Namel3ssError(
            build_guidance_message(
                what="Rollback cannot apply migrations.",
                why="Rollback reverts the last promotion only.",
                fix="Run rollback alone.",
                example="n3 ship --back",
            )
        )
    return app_arg, target, build_id, rollback, with_migrations


def _maybe_handle_migrations(app_snapshot: Path, project_root: Path, *, with_migrations: bool) -> None:
    program, _sources = load_program(app_snapshot.as_posix())
    set_audit_root(project_root)
    records = list(getattr(program, "records", []))
    if not records:
        return
    migration_state = load_migration_state(project_root)
    if not migration_state.last_plan_id and not migration_state.applied_plan_id and not with_migrations:
        return
    status = status_payload(records, project_root=project_root)
    if status.get("plan_changed") and not with_migrations:
        raise Namel3ssError(_plan_changed_message())
    if status.get("pending") and not with_migrations:
        raise Namel3ssError(_pending_migrations_message())
    if with_migrations and (status.get("pending") or status.get("plan_changed")):
        config = load_config(app_path=app_snapshot, root=project_root)
        store = create_store(config=config)
        try:
            payload = apply_plan(records, project_root=project_root, store=store)
        finally:
            _close_store(store)
        plan = payload.get("plan") if isinstance(payload.get("plan"), dict) else {}
        plan_id = plan.get("plan_id") or "unknown"
        print(f"Applied migrations: {plan_id}")


def _close_store(store) -> None:
    closer = getattr(store, "close", None)
    if callable(closer):
        try:
            closer()
        except Exception:
            pass


def _pending_migrations_message() -> str:
    return build_guidance_message(
        what="Pending migrations detected.",
        why="Data schema changes must be applied before promotion.",
        fix="Apply migrations or ship with --with-migrations.",
        example="n3 migrate apply",
    )


def _plan_changed_message() -> str:
    return build_guidance_message(
        what="Migration plan changed.",
        why="Schema changes differ from the last planned migrations.",
        fix="Regenerate and apply the migration plan before promotion.",
        example="n3 migrate plan",
    )


__all__ = ["run_promote_command"]
