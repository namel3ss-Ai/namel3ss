from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from namel3ss.cli.app_path import resolve_app_path
from namel3ss.editor.server import EditorServer
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.utils.json_tools import dumps_pretty


@dataclass
class _EditorParams:
    app_arg: str | None
    port: int | None
    json_mode: bool


def run_editor_command(args: list[str]) -> int:
    params = _parse_args(args)
    app_path = resolve_app_path(params.app_arg)
    server = EditorServer(Path(app_path), port=params.port)
    server.bind()
    if params.json_mode:
        payload = {
            "status": "ok",
            "port": server.bound_port,
            "url": f"http://127.0.0.1:{server.bound_port}",
            "app_path": app_path.as_posix(),
        }
        print(dumps_pretty(payload))
    else:
        print(f"Editor server listening on http://127.0.0.1:{server.bound_port}")
    try:
        server.start(background=False)
    except KeyboardInterrupt:
        return 0
    return 0


def _parse_args(args: list[str]) -> _EditorParams:
    app_arg = None
    port: int | None = None
    json_mode = False
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--json":
            json_mode = True
            i += 1
            continue
        if arg == "--port":
            if i + 1 >= len(args):
                raise Namel3ssError(
                    build_guidance_message(
                        what="--port flag is missing a value.",
                        why="Editor needs a port number.",
                        fix="Provide a port after --port.",
                        example="n3 editor --port 7333",
                    )
                )
            try:
                port = int(args[i + 1])
            except ValueError as err:
                raise Namel3ssError("Port must be an integer") from err
            i += 2
            continue
        if arg.startswith("--"):
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Unknown flag '{arg}'.",
                    why="Supported flags: --port, --json.",
                    fix="Remove the unsupported flag.",
                    example="n3 editor --port 7333 --json",
                )
            )
        if arg == "stop":
            raise Namel3ssError(
                build_guidance_message(
                    what="Editor stop is not available in this release.",
                    why="The editor server runs in the foreground.",
                    fix="Terminate the process to stop the server.",
                    example="Press Ctrl+C",
                )
            )
        if app_arg is None:
            app_arg = arg
            i += 1
            continue
        raise Namel3ssError(
            build_guidance_message(
                what="Too many positional arguments.",
                why="Editor accepts at most one app path.",
                fix="Provide a single app.ai path or none.",
                example="n3 editor app.ai",
            )
        )
    return _EditorParams(app_arg, port, json_mode)


__all__ = ["run_editor_command"]
