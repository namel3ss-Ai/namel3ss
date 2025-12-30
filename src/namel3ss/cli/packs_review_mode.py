from __future__ import annotations

from pathlib import Path

from namel3ss.cli.app_path import resolve_app_path
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.packs.authoring_paths import resolve_pack_dir
from namel3ss.runtime.packs.authoring_review import review_pack
from namel3ss.utils.json_tools import dumps_pretty


def run_packs_review(args: list[str], *, json_mode: bool) -> int:
    if not args or args[0] in {"help", "-h", "--help"}:
        _print_usage()
        return 0
    if len(args) != 1:
        raise Namel3ssError(_unknown_args_message(args[1:]))
    target = args[0]
    pack_dir, app_root = _resolve_pack_and_root(target)
    review = review_pack(pack_dir, app_root)
    if json_mode:
        print(dumps_pretty(review.payload))
        return 0 if review.status != "fail" else 1
    print(f"Pack review: {review.status}")
    print(f"Pack: {review.payload['pack_id']} version {review.payload['version']}")
    print(f"Tools: {', '.join(review.payload['tools'])}")
    print(f"Runners: {', '.join(review.payload['runners'])}")
    collisions = review.payload.get("collisions") or []
    if collisions:
        print("Collisions:")
        for name in collisions:
            print(f"- {name}")
    issues = review.payload.get("issues") or []
    if issues:
        print("Issues:")
        for message in issues:
            print(f"- {message}")
    return 0 if review.status != "fail" else 1


def _print_usage() -> None:
    usage = """Usage:
  n3 packs review path_or_pack --json
  Notes:
    flags are optional unless stated
"""
    print(usage.strip())


def _resolve_pack_and_root(target: str) -> tuple[Path, Path | None]:
    path = Path(target)
    if path.exists():
        app_root = _try_app_root()
        return path, app_root
    app_path = resolve_app_path(None)
    return resolve_pack_dir(app_path.parent, target), app_path.parent


def _try_app_root() -> Path | None:
    try:
        return resolve_app_path(None).parent
    except Namel3ssError:
        return None


def _unknown_args_message(args: list[str]) -> str:
    return build_guidance_message(
        what=f"Unknown arguments: {' '.join(args)}.",
        why="n3 packs review accepts a single path or pack id.",
        fix="Remove the extra arguments.",
        example="n3 packs review ./pack",
    )


__all__ = ["run_packs_review"]
