from __future__ import annotations

import sys
from dataclasses import dataclass

from namel3ss.cli.app_path import resolve_app_path
from namel3ss.docs.portal import DocsRunner, DEFAULT_DOCS_PORT
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.errors.render import format_error
from namel3ss.cli.text_output import prepare_cli_text


@dataclass(frozen=True)
class _DocsParams:
    app_arg: str | None
    port: int | None


def run_docs_command(args: list[str]) -> int:
    try:
        params = _parse_args(args)
        app_path = resolve_app_path(params.app_arg)
        runner = DocsRunner(app_path, port=params.port or DEFAULT_DOCS_PORT)
        print(f"Docs: http://127.0.0.1:{runner.port}/docs")
        try:
            runner.start(background=False)
        except KeyboardInterrupt:
            print("Docs server stopped.")
        return 0
    except Namel3ssError as err:
        message = format_error(err, None)
        print(prepare_cli_text(message), file=sys.stderr)
        return 1


def _parse_args(args: list[str]) -> _DocsParams:
    app_arg = None
    port: int | None = None
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--port":
            if i + 1 >= len(args):
                raise Namel3ssError(
                    build_guidance_message(
                        what="--port flag is missing a value.",
                        why="Docs needs a port number.",
                        fix="Provide a numeric port value.",
                        example="n3 docs --port 7341",
                    )
                )
            try:
                port = int(args[i + 1])
            except ValueError as err:
                raise Namel3ssError(
                    build_guidance_message(
                        what="Port must be an integer.",
                        why="Non-numeric ports are not supported.",
                        fix="Provide a numeric port value.",
                        example="n3 docs --port 7341",
                    )
                ) from err
            i += 2
            continue
        if arg.startswith("--"):
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Unknown flag '{arg}'.",
                    why="Docs supports --port only.",
                    fix="Remove the unsupported flag.",
                    example="n3 docs --port 7341",
                )
            )
        if app_arg is None:
            app_arg = arg
            i += 1
            continue
        raise Namel3ssError(
            build_guidance_message(
                what="Too many positional arguments.",
                why="Docs accepts at most one app path.",
                fix="Provide a single app.ai path or none.",
                example="n3 docs app.ai",
            )
        )
    return _DocsParams(app_arg=app_arg, port=port)


__all__ = ["run_docs_command"]
