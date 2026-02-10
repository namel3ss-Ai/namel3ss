from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys

from namel3ss.cli.text_output import prepare_cli_text
from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.errors.render import format_error
from namel3ss.packaging.deploy import deploy_bundle_archive


@dataclass(frozen=True)
class DeployCommandParams:
    archive_path: Path
    out_dir: Path | None
    channels: tuple[str, ...]
    json_mode: bool


def run_deploy_cli_command(args: list[str]) -> int:
    if args and args[0] in {"help", "-h", "--help"}:
        print(_usage_message())
        return 0
    try:
        params = _parse_args(args)
        bundle = deploy_bundle_archive(
            params.archive_path,
            out_dir=params.out_dir,
            channels=params.channels,
        )
        payload = {
            "ok": True,
            "archive": params.archive_path.as_posix(),
            "channels": list(params.channels),
            "deployment": bundle.as_dict(),
        }
        if params.json_mode:
            print(canonical_json_dumps(payload, pretty=True, drop_run_keys=False))
            return 0
        print(f"Deploy report: {bundle.report_path.as_posix()}")
        print(f"Channels: {', '.join(params.channels)}")
        return 0
    except Namel3ssError as err:
        print(prepare_cli_text(format_error(err, None)), file=sys.stderr)
        return 1


def _parse_args(args: list[str]) -> DeployCommandParams:
    archive_path: Path | None = None
    out_dir: Path | None = None
    channels: list[str] = ["filesystem"]
    json_mode = False

    index = 0
    while index < len(args):
        token = args[index]
        if token == "--json":
            json_mode = True
            index += 1
            continue
        if token in {"--out", "--channel"}:
            if index + 1 >= len(args):
                raise Namel3ssError(_missing_flag_value_message(token))
            value = args[index + 1]
            if token == "--out":
                out_dir = Path(value)
            else:
                channels = _parse_channels(value)
            index += 2
            continue
        if token.startswith("--"):
            raise Namel3ssError(_unknown_flag_message(token))
        if archive_path is not None:
            raise Namel3ssError(_too_many_positionals_message())
        archive_path = Path(token)
        index += 1

    resolved_archive = _resolve_archive_path(archive_path)
    return DeployCommandParams(
        archive_path=resolved_archive,
        out_dir=out_dir,
        channels=tuple(channels),
        json_mode=json_mode,
    )


def _resolve_archive_path(value: Path | None) -> Path:
    if value is not None:
        path = value.expanduser().resolve()
        if not path.exists():
            raise Namel3ssError(_missing_archive_message(path))
        return path
    candidates = sorted(path.resolve() for path in Path.cwd().glob("dist/*.n3bundle.zip") if path.is_file())
    if not candidates:
        raise Namel3ssError(_missing_archive_message(Path("dist/*.n3bundle.zip")))
    return candidates[-1]


def _parse_channels(value: str) -> list[str]:
    channels = [item.strip().lower() for item in value.split(",") if item.strip()]
    if not channels:
        raise Namel3ssError("--channel requires at least one value.")
    return sorted(set(channels))


def _missing_archive_message(path: Path) -> str:
    return build_guidance_message(
        what=f"Deploy archive not found: {path.as_posix()}.",
        why="deploy requires an existing .n3bundle.zip build output.",
        fix="Run `n3 build` first, then pass the produced archive.",
        example="n3 deploy dist/app_service.n3bundle.zip --channel filesystem",
    )


def _unknown_flag_message(flag: str) -> str:
    return build_guidance_message(
        what=f"Unknown deploy flag '{flag}'.",
        why="deploy supports --out, --channel, and --json.",
        fix="Remove unsupported flags.",
        example="n3 deploy dist/app_service.n3bundle.zip --channel filesystem",
    )


def _missing_flag_value_message(flag: str) -> str:
    return build_guidance_message(
        what=f"{flag} requires a value.",
        why="This flag configures deploy destination or channel selection.",
        fix="Pass a value immediately after the flag.",
        example="n3 deploy dist/app_service.n3bundle.zip --out deploy",
    )


def _too_many_positionals_message() -> str:
    return build_guidance_message(
        what="deploy accepts only one archive path.",
        why="Additional positional values make deploy target selection ambiguous.",
        fix="Pass one archive and use flags for options.",
        example="n3 deploy dist/app_service.n3bundle.zip --channel filesystem",
    )


def _usage_message() -> str:
    return (
        "Usage:\n"
        "  n3 deploy [archive.n3bundle.zip] [--out DIR] [--channel filesystem|container|pypi|npm] [--json]"
    )


__all__ = ["run_deploy_cli_command"]
