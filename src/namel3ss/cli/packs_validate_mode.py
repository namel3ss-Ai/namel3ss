from __future__ import annotations

from pathlib import Path

from namel3ss.cli.app_path import resolve_app_path
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.packs.authoring_paths import resolve_pack_dir
from namel3ss.runtime.capabilities.effective import summarize_guarantees
from namel3ss.runtime.packs.authoring_validate import PackIssue, validate_pack
from namel3ss.runtime.packs.capabilities import capabilities_summary, load_pack_capabilities
from namel3ss.utils.json_tools import dumps_pretty


def run_packs_validate(args: list[str], *, json_mode: bool) -> int:
    if not args or args[0] in {"help", "-h", "--help"}:
        _print_usage()
        return 0
    strict = False
    target = None
    for item in args:
        if item == "--strict":
            strict = True
            continue
        if target is None:
            target = item
            continue
        raise Namel3ssError(_unknown_args_message([item]))
    if not target:
        raise Namel3ssError(_missing_target_message())
    pack_dir = _resolve_pack_dir(target)
    result = validate_pack(pack_dir)
    errors = list(result.errors)
    warnings = list(result.warnings)
    if strict and warnings:
        errors.extend(warnings)
        warnings = []
    status = _status_from_issues(errors, warnings)
    payload = {
        "status": status,
        "pack_id": result.pack_id,
        "errors": [issue.message for issue in errors],
        "warnings": [issue.message for issue in warnings],
        "strict": strict,
    }
    payload.update(_capability_payload(pack_dir))
    if json_mode:
        print(dumps_pretty(payload))
        return 0 if status != "fail" else 1
    print(f"Pack validation: {status}")
    _print_issues("Errors", errors)
    _print_issues("Warnings", warnings)
    return 0 if status != "fail" else 1


def _print_usage() -> None:
    usage = """Usage:
  n3 packs validate path_or_pack --strict --json
  Notes:
    flags are optional unless stated
"""
    print(usage.strip())


def _print_issues(label: str, issues: list[PackIssue]) -> None:
    if not issues:
        return
    print(f"{label}:")
    for issue in issues:
        print(f"- {issue.message}")


def _resolve_pack_dir(value: str) -> Path:
    path = Path(value)
    if path.exists():
        return path
    app_path = resolve_app_path(None)
    return resolve_pack_dir(app_path.parent, value)


def _missing_target_message() -> str:
    return build_guidance_message(
        what="Pack target is missing.",
        why="You must provide a path or pack id.",
        fix="Pass a pack directory or pack id.",
        example="n3 packs validate ./packs/my_pack",
    )


def _unknown_args_message(args: list[str]) -> str:
    return build_guidance_message(
        what=f"Unknown arguments: {' '.join(args)}.",
        why="n3 packs validate only accepts --strict.",
        fix="Remove the extra arguments.",
        example="n3 packs validate ./pack --strict",
    )


def _status_from_issues(errors: list[PackIssue], warnings: list[PackIssue]) -> str:
    if errors:
        return "fail"
    if warnings:
        return "warn"
    return "ok"


def _capability_payload(pack_dir: Path) -> dict[str, object]:
    try:
        caps = load_pack_capabilities(pack_dir)
    except Exception:
        return {"capabilities": {}, "guarantees": {}}
    return {
        "capabilities": capabilities_summary(caps) if caps else {},
        "guarantees": summarize_guarantees(caps) if caps else {},
    }


__all__ = ["run_packs_validate"]
