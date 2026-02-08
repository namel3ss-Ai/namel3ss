from __future__ import annotations

import sys

from namel3ss.cli.app_path import default_missing_app_message, resolve_app_path
from namel3ss.cli.devex import parse_project_overrides
from namel3ss.cli.headless_api_flags import (
    extract_headless_api_flags,
    resolve_headless_api_token,
    resolve_headless_cors_origins,
)
from namel3ss.cli.text_output import prepare_cli_text
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.errors.render import format_error
from namel3ss.runtime.capabilities.feature_gate import require_app_capability
from namel3ss.runtime.service_runner import DEFAULT_SERVICE_PORT, ServiceRunner
from namel3ss.secrets import set_audit_root, set_engine_target


class _ServeParams:
    def __init__(
        self,
        *,
        app_arg: str | None,
        port: int | None,
        dry: bool,
        headless: bool,
    ) -> None:
        self.app_arg = app_arg
        self.port = port
        self.dry = dry
        self.headless = headless



def run_serve_command(args: list[str]) -> int:
    try:
        overrides, remaining = parse_project_overrides(args)
        remaining, headless_api = extract_headless_api_flags(remaining)
        resolved_api_token = resolve_headless_api_token(headless_api.api_token)
        resolved_cors_origins = resolve_headless_cors_origins(headless_api.cors_origins)
        params = _parse_args(remaining)
        if params.app_arg and overrides.app_path:
            raise Namel3ssError("App path was provided twice. Use either an explicit app path or --app.")
        app_path = resolve_app_path(
            params.app_arg or overrides.app_path,
            project_root=overrides.project_root,
            search_parents=False,
            missing_message=default_missing_app_message("serve"),
        )
        project_root = app_path.parent
        require_app_capability(app_path, "service")
        set_engine_target("service")
        set_audit_root(project_root)
        port = params.port or DEFAULT_SERVICE_PORT
        runner = ServiceRunner(
            app_path,
            "service",
            build_id=None,
            port=port,
            headless=params.headless,
            headless_api_token=resolved_api_token,
            headless_cors_origins=resolved_cors_origins,
            require_service_capability=True,
        )
        if params.dry:
            print(f"Service: http://127.0.0.1:{port}/")
            return 0
        print(f"Service: http://127.0.0.1:{port}/")
        try:
            runner.start(background=False)
        except KeyboardInterrupt:
            print("Service stopped.")
        return 0
    except Namel3ssError as err:
        print(prepare_cli_text(format_error(err, None)), file=sys.stderr)
        return 1



def _parse_args(args: list[str]) -> _ServeParams:
    app_arg = None
    port: int | None = None
    dry = False
    headless = False
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--port":
            if i + 1 >= len(args):
                raise Namel3ssError(
                    build_guidance_message(
                        what="--port flag is missing a value.",
                        why="A port number must follow --port.",
                        fix="Pass an integer port.",
                        example="n3 serve app.ai --port 8787",
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
                        example="n3 serve app.ai --port 8787",
                    )
                ) from err
            i += 2
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
                    why="Supported flags: --port, --dry, --headless.",
                    fix="Remove the unsupported flag.",
                    example="n3 serve app.ai --port 8787",
                )
            )
        if app_arg is None:
            app_arg = arg
            i += 1
            continue
        raise Namel3ssError(
            build_guidance_message(
                what="Too many positional arguments.",
                why="Serve accepts at most one app path.",
                fix="Provide a single app.ai path or none.",
                example="n3 serve app.ai",
            )
        )
    return _ServeParams(app_arg=app_arg, port=port, dry=dry, headless=headless)


__all__ = ["run_serve_command"]
