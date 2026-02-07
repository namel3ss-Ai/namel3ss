from __future__ import annotations

import sys
from pathlib import Path

from namel3ss.cli.app_loader import load_program
from namel3ss.cli.app_path import default_missing_app_message, resolve_app_path
from namel3ss.cli.devex import parse_project_overrides
from namel3ss.cli.text_output import prepare_cli_text
from namel3ss.cli.ui_mode import render_manifest
from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.errors.render import format_error


def run_manifest_command(args: list[str]) -> int:
    try:
        overrides, remaining = parse_project_overrides(args)
        json_mode, output_path, app_arg = _parse_args(remaining)
        app_path = resolve_app_path(
            app_arg or overrides.app_path,
            project_root=overrides.project_root,
            search_parents=False,
            missing_message=default_missing_app_message("manifest"),
        )
        program_ir, _sources = load_program(app_path.as_posix())
        manifest = render_manifest(program_ir)
        payload = {
            "ok": True,
            "app_path": app_path.as_posix(),
            "manifest": manifest,
        }
        if output_path is not None:
            target = Path(output_path).expanduser().resolve()
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(canonical_json_dumps(payload, pretty=True, drop_run_keys=False) + "\n", encoding="utf-8")
            if json_mode:
                print(canonical_json_dumps({"ok": True, "path": target.as_posix()}, pretty=True, drop_run_keys=False))
            else:
                print(f"Manifest written: {target.as_posix()}")
            return 0
        print(canonical_json_dumps(payload, pretty=True, drop_run_keys=False))
        return 0
    except Namel3ssError as err:
        print(prepare_cli_text(format_error(err, None)), file=sys.stderr)
        return 1


def _parse_args(args: list[str]) -> tuple[bool, str | None, str | None]:
    json_mode = False
    output_path: str | None = None
    app_arg: str | None = None
    i = 0
    while i < len(args):
        arg = args[i]
        if arg in {"--json"}:
            json_mode = True
            i += 1
            continue
        if arg == "--out":
            if i + 1 >= len(args):
                raise Namel3ssError(
                    build_guidance_message(
                        what="--out is missing a path value.",
                        why="Manifest output file path is required after --out.",
                        fix="Provide a path after --out.",
                        example="n3 manifest app.ai --out ./manifest.json",
                    )
                )
            output_path = args[i + 1]
            i += 2
            continue
        if arg.startswith("--"):
            raise Namel3ssError(_unknown_flag_message(arg))
        if app_arg is None:
            app_arg = arg
            i += 1
            continue
        raise Namel3ssError(
            build_guidance_message(
                what="manifest accepts at most one app path.",
                why="More than one positional argument was provided.",
                fix="Provide a single app path or rely on default app.ai.",
                example="n3 manifest app.ai",
            )
        )
    return json_mode, output_path, app_arg


def _unknown_flag_message(flag: str) -> str:
    return build_guidance_message(
        what=f"Unknown flag '{flag}'.",
        why="manifest supports --json and --out only.",
        fix="Remove unsupported flags.",
        example="n3 manifest app.ai --json",
    )


__all__ = ["run_manifest_command"]
