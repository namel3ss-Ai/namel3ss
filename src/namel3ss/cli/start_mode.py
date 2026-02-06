from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from namel3ss.cli.app_path import resolve_app_path
from namel3ss.cli.builds import load_build_metadata, resolve_build_id
from namel3ss.cli.devex import parse_project_overrides
from namel3ss.cli.targets import parse_target
from namel3ss.cli.text_output import prepare_cli_text
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.errors.render import format_error
from namel3ss.runtime.production_server import DEFAULT_START_PORT, ProductionRunner
from namel3ss.secrets import set_audit_root, set_engine_target


@dataclass(frozen=True)
class _StartParams:
    app_arg: str | None
    target_raw: str | None
    port: int | None
    build_id: str | None
    headless: bool


def run_start_command(args: list[str]) -> int:
    try:
        overrides, remaining = parse_project_overrides(args)
        params = _parse_args(remaining)
        if params.app_arg and overrides.app_path:
            raise Namel3ssError("App path was provided twice. Use either an explicit app path or --app.")
        app_path = resolve_app_path(params.app_arg or overrides.app_path, project_root=overrides.project_root)
        project_root = app_path.parent
        target = parse_target(params.target_raw or "service")
        if target.name != "service":
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Unsupported target '{target.name}'.",
                    why="n3 start only supports the service target.",
                    fix="Run with --target service or omit the flag.",
                    example="n3 start --target service",
                )
            )
        set_engine_target(target.name)
        set_audit_root(project_root)
        build_id = resolve_build_id(project_root, target.name, params.build_id)
        if not build_id:
            raise Namel3ssError(
                build_guidance_message(
                    what=f"No build found for target '{target.name}'.",
                    why="n3 start requires a completed build.",
                    fix="Run `n3 build` for this target first.",
                    example="n3 build --target service",
                )
            )
        build_path, meta = load_build_metadata(project_root, target.name, build_id)
        app_relative_path = meta.get("app_relative_path")
        if not isinstance(app_relative_path, str) or not app_relative_path:
            raise Namel3ssError(
                build_guidance_message(
                    what="Build metadata is missing the app path.",
                    why="app_relative_path was not recorded.",
                    fix="Re-run `n3 build` for this target.",
                    example="n3 build --target service",
                )
            )
        app_path = project_root / app_relative_path
        artifacts = meta.get("artifacts") if isinstance(meta, dict) else None
        port = params.port or DEFAULT_START_PORT
        runner = ProductionRunner(
            build_path,
            app_path,
            build_id=build_id,
            target=target.name,
            port=port,
            artifacts=artifacts if isinstance(artifacts, dict) else None,
            headless=params.headless,
        )
        print(f"Start: http://127.0.0.1:{port}/")
        print(f"Build: {build_id}")
        try:
            runner.start(background=False)
        except KeyboardInterrupt:
            print("Production server stopped.")
        return 0
    except Namel3ssError as err:
        message = format_error(err, None)
        print(prepare_cli_text(message), file=sys.stderr)
        return 1


def _parse_args(args: list[str]) -> _StartParams:
    app_arg = None
    target = None
    port: int | None = None
    build_id = None
    headless = False
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--target":
            if i + 1 >= len(args):
                raise Namel3ssError(
                    build_guidance_message(
                        what="--target flag is missing a value.",
                        why="Start requires a target name.",
                        fix="Provide service as the target.",
                        example="n3 start --target service",
                    )
                )
            target = args[i + 1]
            i += 2
            continue
        if arg == "--port":
            if i + 1 >= len(args):
                raise Namel3ssError(
                    build_guidance_message(
                        what="--port flag is missing a value.",
                        why="A port number must follow --port.",
                        fix="Pass an integer port.",
                        example="n3 start --port 8787",
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
                        example="n3 start --port 8787",
                    )
                ) from err
            i += 2
            continue
        if arg == "--build":
            if i + 1 >= len(args):
                raise Namel3ssError(
                    build_guidance_message(
                        what="--build flag is missing a value.",
                        why="A build id must follow --build.",
                        fix="Provide the build id to start from.",
                        example="n3 start --build service-abc123",
                    )
                )
            build_id = args[i + 1]
            i += 2
            continue
        if arg == "--headless":
            headless = True
            i += 1
            continue
        if arg.startswith("--"):
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Unknown flag '{arg}'.",
                    why="Supported flags: --target, --port, --build, --headless.",
                    fix="Remove the unsupported flag.",
                    example="n3 start --target service",
                )
            )
        if app_arg is None:
            app_arg = arg
            i += 1
            continue
        raise Namel3ssError(
            build_guidance_message(
                what="Too many positional arguments.",
                why="Start accepts at most one app path.",
                fix="Provide a single app.ai path or none.",
                example="n3 start app.ai",
            )
        )
    return _StartParams(app_arg=app_arg, target_raw=target, port=port, build_id=build_id, headless=headless)


__all__ = ["run_start_command"]
