from __future__ import annotations

from pathlib import Path

from namel3ss.cli.app_path import resolve_app_path
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.registry.ops import add_bundle_to_registry
from namel3ss.utils.json_tools import dumps_pretty


def run_registry_add(args: list[str], *, json_mode: bool) -> int:
    if not args or args[0] in {"help", "-h", "--help"}:
        _print_usage()
        return 0
    if len(args) > 1:
        raise Namel3ssError(_unknown_args_message(args[1:]))
    bundle_path = Path(args[0]).expanduser().resolve()
    if not bundle_path.exists():
        raise Namel3ssError(_missing_path_message(bundle_path))
    app_path = resolve_app_path(None)
    app_root = app_path.parent
    entry = add_bundle_to_registry(app_root, bundle_path)
    payload = {
        "status": "ok",
        "pack_id": entry.pack_id,
        "pack_version": entry.pack_version,
        "pack_digest": entry.pack_digest,
        "entry": entry.to_dict(),
    }
    if json_mode:
        print(dumps_pretty(payload))
        return 0
    print(f"Registry entry added: {entry.pack_id}@{entry.pack_version}")
    print(f"Digest: {entry.pack_digest}")
    return 0


def _print_usage() -> None:
    usage = """Usage:
  n3 registry add bundle_path --json
  Notes:
    flags are optional unless stated
"""
    print(usage.strip())


def _unknown_args_message(args: list[str]) -> str:
    return build_guidance_message(
        what=f"Unknown arguments: {' '.join(args)}.",
        why="n3 registry add accepts a single bundle path.",
        fix="Remove the extra arguments and try again.",
        example="n3 registry add ./dist/team.pack-0.1.0.n3pack.zip",
    )


def _missing_path_message(path: Path) -> str:
    return build_guidance_message(
        what="Bundle path is missing.",
        why=f"Expected {path.as_posix()} to exist.",
        fix="Provide a valid .n3pack.zip path.",
        example="n3 registry add ./dist/team.pack-0.1.0.n3pack.zip",
    )


__all__ = ["run_registry_add"]
