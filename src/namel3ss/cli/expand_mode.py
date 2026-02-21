from __future__ import annotations

import sys

from namel3ss.cli.app_path import default_missing_app_message, resolve_app_path
from namel3ss.cli.devex import parse_project_overrides
from namel3ss.cli.text_output import prepare_cli_text
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.errors.render import format_error
from namel3ss.parser.preset_expansion import expand_language_presets


def run_expand_command(args: list[str]) -> int:
    try:
        overrides, remaining = parse_project_overrides(args)
        app_arg = _parse_args(remaining)
        app_path = resolve_app_path(
            app_arg or overrides.app_path,
            project_root=overrides.project_root,
            search_parents=False,
            missing_message=default_missing_app_message("expand"),
        )
        source = app_path.read_text(encoding="utf-8")
        expanded = expand_language_presets(source)
        print(expanded, end="")
        return 0
    except Namel3ssError as err:
        print(prepare_cli_text(format_error(err, None)), file=sys.stderr)
        return 1


def _parse_args(args: list[str]) -> str | None:
    app_arg: str | None = None
    for token in args:
        if token.startswith("--"):
            raise Namel3ssError(_unknown_flag_message(token))
        if app_arg is not None:
            raise Namel3ssError(_too_many_args_message())
        app_arg = token
    return app_arg


def _unknown_flag_message(flag: str) -> str:
    return build_guidance_message(
        what=f"Unknown flag '{flag}'.",
        why="expand supports only one optional app path.",
        fix="Remove unsupported flags.",
        example="n3 expand app.ai",
    )


def _too_many_args_message() -> str:
    return build_guidance_message(
        what="expand accepts at most one app path.",
        why="More than one positional argument was provided.",
        fix="Provide a single app path or rely on default app.ai.",
        example="n3 expand app.ai",
    )


__all__ = ["run_expand_command"]
