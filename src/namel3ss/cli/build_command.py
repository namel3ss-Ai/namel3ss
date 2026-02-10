from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys

from namel3ss.cli.text_output import prepare_cli_text
from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.errors.render import format_error
from namel3ss.packaging.build import build_deployable_bundle


@dataclass(frozen=True)
class BuildCommandParams:
    app_path: Path
    out_dir: Path | None
    target: str
    profile: bool
    profile_iterations: int
    json_mode: bool


def run_build_cli_command(args: list[str]) -> int:
    if args and args[0] in {"help", "-h", "--help"}:
        print(_usage_message())
        return 0
    try:
        params = _parse_args(args)
        bundle = build_deployable_bundle(
            params.app_path,
            out_dir=params.out_dir,
            target=params.target,
            include_profile=params.profile,
            profile_iterations=params.profile_iterations,
        )
        payload = {
            "ok": True,
            "app": params.app_path.as_posix(),
            "target": params.target,
            "bundle": bundle.as_dict(),
        }
        if params.json_mode:
            print(canonical_json_dumps(payload, pretty=True, drop_run_keys=False))
            return 0
        print(f"Build ready: {bundle.root.as_posix()}")
        print(f"Archive: {bundle.archive.as_posix()}")
        print(f"Artifacts: {len(bundle.artifacts)}")
        return 0
    except Namel3ssError as err:
        print(prepare_cli_text(format_error(err, None)), file=sys.stderr)
        return 1


def _parse_args(args: list[str]) -> BuildCommandParams:
    app_path: Path | None = None
    out_dir: Path | None = None
    target = "service"
    profile = False
    profile_iterations = 1
    json_mode = False

    index = 0
    while index < len(args):
        token = args[index]
        if token == "--json":
            json_mode = True
            index += 1
            continue
        if token == "--profile":
            profile = True
            index += 1
            continue
        if token in {"--out", "--target", "--profile-iterations"}:
            if index + 1 >= len(args):
                raise Namel3ssError(_missing_flag_value_message(token))
            value = args[index + 1]
            if token == "--out":
                out_dir = Path(value)
            elif token == "--target":
                target = value
            else:
                profile_iterations = _parse_positive_int(value, flag=token)
            index += 2
            continue
        if token.startswith("--"):
            raise Namel3ssError(_unknown_flag_message(token))
        if app_path is not None:
            raise Namel3ssError(_too_many_positionals_message())
        app_path = Path(token)
        index += 1

    resolved = _resolve_app_path(app_path)
    return BuildCommandParams(
        app_path=resolved,
        out_dir=out_dir,
        target=target,
        profile=profile,
        profile_iterations=profile_iterations,
        json_mode=json_mode,
    )


def _resolve_app_path(value: Path | None) -> Path:
    candidate = value if value is not None else Path("app.ai")
    resolved = candidate.expanduser().resolve()
    if not resolved.exists():
        raise Namel3ssError(_missing_app_message(resolved))
    return resolved


def _parse_positive_int(value: str, *, flag: str) -> int:
    try:
        parsed = int(value)
    except ValueError as err:
        raise Namel3ssError(f"{flag} must be an integer.") from err
    if parsed < 1:
        raise Namel3ssError(f"{flag} must be >= 1.")
    return parsed


def _missing_app_message(path: Path) -> str:
    return build_guidance_message(
        what=f"Build app file not found: {path.as_posix()}.",
        why="build needs a valid .ai file path.",
        fix="Provide the app path or run from a project folder containing app.ai.",
        example="n3 build app.ai --out dist",
    )


def _unknown_flag_message(flag: str) -> str:
    return build_guidance_message(
        what=f"Unknown build flag '{flag}'.",
        why="build supports --out, --target, --profile, --profile-iterations, and --json.",
        fix="Remove unsupported flags.",
        example="n3 build app.ai --target service --profile",
    )


def _missing_flag_value_message(flag: str) -> str:
    return build_guidance_message(
        what=f"{flag} requires a value.",
        why="This flag controls build output or profiling settings.",
        fix="Pass a value immediately after the flag.",
        example="n3 build app.ai --target service",
    )


def _too_many_positionals_message() -> str:
    return build_guidance_message(
        what="build accepts only one app file argument.",
        why="Additional positional values make target resolution ambiguous.",
        fix="Keep only one app path and move options into flags.",
        example="n3 build app.ai --out dist",
    )


def _usage_message() -> str:
    return (
        "Usage:\n"
        "  n3 build [app.ai] [--out DIR] [--target local|service|edge] "
        "[--profile] [--profile-iterations N] [--json]"
    )


__all__ = ["run_build_cli_command"]
