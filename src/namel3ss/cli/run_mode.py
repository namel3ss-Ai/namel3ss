from __future__ import annotations
import re
import sys
from pathlib import Path

from namel3ss.cli.app_loader import load_program
from namel3ss.cli.app_path import resolve_app_path
from namel3ss.cli.devex import parse_project_overrides
from namel3ss.cli.builds import app_path_from_metadata, load_build_metadata, read_latest_build_id
from namel3ss.cli.demo_support import CLEARORDERS_NAME, is_clearorders_demo
from namel3ss.cli.first_run import is_first_run
from namel3ss.cli.open_url import open_url, should_open_url
from namel3ss.cli.promotion_state import load_state
from namel3ss.cli.runner import run_flow
from namel3ss.cli.targets import parse_target
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.errors.render import format_error, format_first_run_error
from namel3ss.runtime.service_runner import DEFAULT_SERVICE_PORT, ServiceRunner
from namel3ss.utils.json_tools import dumps_pretty
from namel3ss.cli.text_output import prepare_cli_text, prepare_first_run_text
from namel3ss.secrets import set_audit_root, set_engine_target
from namel3ss.traces.plain import format_plain
from namel3ss.traces.schema import TraceEventType


def run_run_command(args: list[str]) -> int:
    sources: dict = {}
    project_root: Path | None = None
    first_run = is_first_run(None, args)
    try:
        overrides, remaining = parse_project_overrides(args)
        params = _parse_args(remaining)
        if params.app_arg and overrides.app_path:
            raise Namel3ssError("App path was provided twice. Use either an explicit app path or --app.")
        app_path = resolve_app_path(params.app_arg or overrides.app_path, project_root=overrides.project_root)
        project_root = app_path.parent
        first_run = is_first_run(project_root, args)
        demo_default = None
        is_demo = params.target_raw is None and is_clearorders_demo(project_root)
        if is_demo:
            demo_default = "service"
        target = parse_target(params.target_raw or demo_default)
        set_engine_target(target.name)
        set_audit_root(project_root)
        run_path, build_id = _resolve_run_path(target.name, project_root, app_path, params.build_id)
        if target.name == "local":
            program_ir, sources = load_program(run_path.as_posix())
            output = run_flow(program_ir, None, sources=sources)
            if params.json_mode:
                print(dumps_pretty(output))
            else:
                print(format_plain(output))
                if params.explain:
                    _print_explain_traces(output)
            return 0
        if target.name == "service":
            port = params.port or DEFAULT_SERVICE_PORT
            runner = ServiceRunner(
                run_path,
                target.name,
                build_id=build_id,
                port=port,
                auto_seed=bool(is_demo and first_run and not params.dry),
            )
            if params.dry:
                print(f"Service runner dry http://127.0.0.1:{port}/health")
                print(f"Build: {build_id or 'working-copy'}")
                return 0
            if is_demo:
                url = f"http://127.0.0.1:{port}/"
                demo_provider = _detect_demo_provider(run_path)
                if first_run:
                    print(f"Running {CLEARORDERS_NAME}")
                    print(f"Open: {url}")
                    if demo_provider == "openai":
                        print("AI provider: OpenAI")
                    print("Press Ctrl+C to stop")
                    if should_open_url(params.no_open):
                        open_url(url)
                else:
                    print(f"Running {CLEARORDERS_NAME} at: {url}")
                    if demo_provider == "openai":
                        print("AI provider: OpenAI")
                    print("Press Ctrl+C to stop.")
            try:
                runner.start(background=False)
            except KeyboardInterrupt:
                print("Service runner stopped.")
            return 0
        if target.name == "edge":
            print("Edge simulator mode (stub).")
            print("This target is limited in the alpha; build artifacts record inputs, engine is stubbed.")
            return 0
        raise Namel3ssError(
            build_guidance_message(
                what=f"Unsupported target '{target.name}'.",
                why="Targets must be local, service, or edge.",
                fix="Choose a supported target.",
                example="n3 run --target local",
            )
        )
    except Namel3ssError as err:
        if first_run:
            message = format_first_run_error(err)
            print(prepare_first_run_text(message), file=sys.stderr)
        else:
            message = format_error(err, sources)
            print(prepare_cli_text(message), file=sys.stderr)
        return 1


class _RunParams:
    def __init__(
        self,
        app_arg: str | None,
        target_raw: str | None,
        port: int | None,
        build_id: str | None,
        dry: bool,
        json_mode: bool,
        no_open: bool,
        explain: bool,
    ):
        self.app_arg = app_arg
        self.target_raw = target_raw
        self.port = port
        self.build_id = build_id
        self.dry = dry
        self.json_mode = json_mode
        self.no_open = no_open
        self.explain = explain


def _parse_args(args: list[str]) -> _RunParams:
    app_arg = None
    target = None
    port: int | None = None
    build_id = None
    dry = False
    json_mode = False
    no_open = False
    explain = False
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--target":
            if i + 1 >= len(args):
                raise Namel3ssError(
                    build_guidance_message(
                        what="--target flag is missing a value.",
                        why="Run requires a target name.",
                        fix="Provide local, service, or edge.",
                        example="n3 run --target service",
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
                        example="n3 run --target service --port 8787",
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
                        example="n3 run --target service --port 8787",
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
                        fix="Provide the build id to run from.",
                        example="n3 run --target service --build service-abc123",
                    )
                )
            build_id = args[i + 1]
            i += 2
            continue
        if arg == "--json":
            json_mode = True
            i += 1
            continue
        if arg == "--explain":
            explain = True
            i += 1
            continue
        if arg == "--no-open":
            no_open = True
            i += 1
            continue
        if arg == "--first-run":
            i += 1
            continue
        if arg == "--dry":
            dry = True
            i += 1
            continue
        if arg.startswith("--"):
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Unknown flag '{arg}'.",
                    why="Supported flags: --target, --port, --build, --dry, --json, --explain, --first-run, --no-open.",
                    fix="Remove the unsupported flag.",
                    example="n3 run --target local",
                )
            )
        if app_arg is None:
            app_arg = arg
            i += 1
            continue
        raise Namel3ssError(
            build_guidance_message(
                what="Too many positional arguments.",
                why="Run accepts at most one app path.",
                fix="Provide a single app.ai path or none.",
                example="n3 run app.ai --target local",
            )
        )
    return _RunParams(app_arg, target, port, build_id, dry, json_mode, no_open, explain)


def _print_explain_traces(output: dict) -> None:
    traces = output.get("traces") if isinstance(output, dict) else None
    if not isinstance(traces, list):
        print("Explain traces: none")
        return
    explain = [trace for trace in traces if trace.get("type") == TraceEventType.EXPRESSION_EXPLAIN]
    if not explain:
        print("Explain traces: none")
        return
    print("Explain traces:")
    print(dumps_pretty(explain))


def _resolve_run_path(target: str, project_root: Path, app_path: Path, build_id: str | None) -> tuple[Path, str | None]:
    chosen_build = build_id
    if target != "local" and chosen_build is None:
        state = load_state(project_root)
        active = state.get("active") or {}
        if active.get("target") == target and active.get("build_id"):
            chosen_build = active.get("build_id")
        elif target in {"service", "edge"}:
            latest = read_latest_build_id(project_root, target)
            if latest:
                chosen_build = latest
    if chosen_build:
        build_path, meta = load_build_metadata(project_root, target, chosen_build)
        return app_path_from_metadata(build_path, meta), chosen_build
    return app_path, None


def _detect_demo_provider(app_path: Path) -> str | None:
    try:
        contents = app_path.read_text(encoding="utf-8")
    except OSError:
        return None
    match = re.search(r'provider\\s+is\\s+"([^"]+)"', contents)
    if not match:
        return None
    return match.group(1).strip().lower()


__all__ = ["run_run_command"]
