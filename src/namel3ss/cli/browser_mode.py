from __future__ import annotations

import sys
from dataclasses import dataclass

from namel3ss.cli.app_path import default_missing_app_message, resolve_app_path
from namel3ss.cli.devex import parse_project_overrides
from namel3ss.cli.headless_api_flags import (
    extract_headless_api_flags,
    resolve_headless_api_token,
    resolve_headless_cors_origins,
)
from namel3ss.cli.open_url import open_url, should_open_url
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.errors.render import format_error
from namel3ss.runtime.dev_server import BrowserRunner, DEFAULT_BROWSER_PORT
from namel3ss.cli.text_output import prepare_cli_text


@dataclass(frozen=True)
class _BrowserParams:
    app_arg: str | None
    port: int | None
    no_open: bool
    debug: bool
    dry: bool
    headless: bool


def run_dev_command(args: list[str]) -> int:
    return _run_browser_command("dev", args)


def run_preview_command(args: list[str]) -> int:
    return _run_browser_command("preview", args)


def _run_browser_command(mode: str, args: list[str]) -> int:
    try:
        overrides, remaining = parse_project_overrides(args)
        remaining, headless_api = extract_headless_api_flags(remaining)
        resolved_api_token = resolve_headless_api_token(headless_api.api_token)
        resolved_cors_origins = resolve_headless_cors_origins(headless_api.cors_origins)
        params = _parse_args(remaining, allow_debug=mode == "dev")
        app_path = resolve_app_path(
            params.app_arg or overrides.app_path,
            project_root=overrides.project_root,
            search_parents=False,
            missing_message=default_missing_app_message(mode),
        )
        port = params.port or DEFAULT_BROWSER_PORT
        runner = BrowserRunner(
            app_path,
            mode=mode,
            port=port,
            debug=params.debug,
            headless=params.headless,
            headless_api_token=resolved_api_token,
            headless_cors_origins=resolved_cors_origins,
        )
        if params.headless:
            url = f"http://127.0.0.1:{runner.bound_port}/api/ui/manifest"
        else:
            url = f"http://127.0.0.1:{runner.bound_port}/"
        label = "Dev" if mode == "dev" else "Preview"
        if params.dry:
            print(f"{label}: {url}")
            return 0
        print(f"{label}: {url}")
        if not params.headless and should_open_url(params.no_open):
            open_url(url)
        try:
            runner.start(background=False)
        except KeyboardInterrupt:
            print(f"{label} server stopped.")
        return 0
    except Namel3ssError as err:
        message = format_error(err, None)
        print(prepare_cli_text(message), file=sys.stderr)
        return 1


def _parse_args(args: list[str], *, allow_debug: bool) -> _BrowserParams:
    app_arg = None
    port: int | None = None
    no_open = False
    debug = False
    dry = False
    headless = False
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--port":
            if i + 1 >= len(args):
                raise Namel3ssError(_missing_flag_value("--port"))
            try:
                port = int(args[i + 1])
            except ValueError as err:
                raise Namel3ssError(
                    build_guidance_message(
                        what="Port must be an integer.",
                        why="Non-numeric ports are not supported.",
                        fix="Provide a numeric port value.",
                        example="n3 dev --port 7340",
                    )
                ) from err
            i += 2
            continue
        if arg == "--no-open":
            no_open = True
            i += 1
            continue
        if arg == "--debug":
            if not allow_debug:
                raise Namel3ssError(
                    build_guidance_message(
                        what="Debug mode is only supported for n3 dev.",
                        why="Preview keeps output production-like.",
                        fix="Drop --debug or run n3 dev instead.",
                        example="n3 dev --debug",
                    )
                )
            debug = True
            i += 1
            continue
        if arg == "--dry":
            dry = True
            i += 1
            continue
        if arg == "--headless":
            headless = True
            i += 1
            continue
        if arg.startswith("--"):
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Unknown flag '{arg}'.",
                    why="Supported flags: --port, --no-open, --debug (dev only), --dry, --headless.",
                    fix="Remove the unsupported flag.",
                    example="n3 dev --port 7340",
                )
            )
        if app_arg is None:
            app_arg = arg
            i += 1
            continue
        raise Namel3ssError(
            build_guidance_message(
                what="Too many positional arguments.",
                why="Dev and preview accept at most one app path.",
                fix="Provide a single app.ai path or none.",
                example="n3 dev app.ai",
            )
        )
    return _BrowserParams(app_arg=app_arg, port=port, no_open=no_open, debug=debug, dry=dry, headless=headless)


def _missing_flag_value(flag: str) -> str:
    return build_guidance_message(
        what=f"{flag} flag is missing a value.",
        why="A value must follow the flag.",
        fix=f"Provide a value after {flag}.",
        example=f"n3 dev {flag} 7340",
    )


__all__ = ["run_dev_command", "run_preview_command"]
