from __future__ import annotations
import os
import re
import sys
from pathlib import Path

from namel3ss.cli.app_loader import load_program
from namel3ss.cli.app_path import default_missing_app_message, resolve_app_path
from namel3ss.cli.devex import parse_project_overrides
from namel3ss.cli.builds import app_path_from_metadata, load_build_metadata, resolve_build_id
from namel3ss.cli.demo_support import DEMO_NAME, is_demo_project
from namel3ss.cli.first_run import is_first_run
from namel3ss.cli.open_url import open_url, should_open_url
from namel3ss.cli.promotion_state import load_state
from namel3ss.cli.runner import run_flow
from namel3ss.cli.targets import parse_target
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.determinism import canonical_json_dumps, canonicalize_run_payload
from namel3ss.errors.render import format_error, format_first_run_error
from namel3ss.runtime.dev_server import BrowserRunner, DEFAULT_BROWSER_PORT
from namel3ss.runtime.service_runner import DEFAULT_SERVICE_PORT, ServiceRunner
from namel3ss.cli.text_output import prepare_cli_text, prepare_first_run_text
from namel3ss.config.loader import load_config
from namel3ss.runtime.performance.config import PerformanceRuntimeConfig, normalize_performance_runtime_config
from namel3ss.runtime.performance.guard import require_performance_capability
from namel3ss.secrets import set_audit_root, set_engine_target
from namel3ss.traces.plain import format_plain
from namel3ss.traces.schema import TraceEventType
from namel3ss.utils.json_tools import dumps_pretty


def run_run_command(args: list[str]) -> int:
    sources: dict = {}
    project_root: Path | None = None
    first_run = is_first_run(None, args)
    try:
        overrides, remaining = parse_project_overrides(args)
        params = _parse_args(remaining)
        if params.app_arg and overrides.app_path:
            raise Namel3ssError("App path was provided twice. Use either an explicit app path or --app.")
        app_path = resolve_app_path(
            params.app_arg or overrides.app_path,
            project_root=overrides.project_root,
            search_parents=False,
            missing_message=default_missing_app_message("run"),
        )
        project_root = app_path.parent
        first_run = is_first_run(project_root, args)
        demo_default = None
        is_demo = params.target_raw is None and is_demo_project(project_root)
        if is_demo:
            demo_default = "service"
        target = parse_target(params.target_raw or demo_default)
        set_engine_target(target.name)
        set_audit_root(project_root)
        _apply_performance_env_overrides(params)
        _validate_performance_settings(
            app_path=app_path,
            project_root=project_root,
            force_check=_has_performance_overrides(params),
        )
        run_path, build_id = _resolve_run_path(target.name, project_root, app_path, params.build_id)
        if target.name == "local":
            if params.json_mode or params.explain:
                program_ir, sources = load_program(run_path.as_posix())
                output = run_flow(program_ir, None, sources=sources)
                render_payload = canonicalize_run_payload(output)
                if params.json_mode:
                    print(canonical_json_dumps(render_payload, pretty=True))
                else:
                    print(format_plain(render_payload))
                    if params.explain:
                        _print_explain_traces(render_payload)
                return 0
            runner = BrowserRunner(
                run_path,
                mode="run",
                port=params.port or DEFAULT_BROWSER_PORT,
                debug=False,
                watch_sources=False,
                engine_target=target.name,
                headless=params.headless,
            )
            try:
                runner.bind()
            except OSError as err:
                raise Namel3ssError(
                    build_guidance_message(
                        what="App server could not start.",
                        why=str(err),
                        fix="Choose another port with --port.",
                        example="n3 run --port 7341",
                    )
                ) from err
            url = (
                f"http://127.0.0.1:{runner.bound_port}/api/ui/manifest"
                if params.headless
                else f"http://127.0.0.1:{runner.bound_port}/"
            )
            if params.dry:
                print(f"App: {url}")
                return 0
            print(f"App: {url}")
            try:
                runner.start(background=False)
            except KeyboardInterrupt:
                print("App server stopped.")
            return 0
        if target.name == "service":
            port = params.port or DEFAULT_SERVICE_PORT
            runner = ServiceRunner(
                run_path,
                target.name,
                build_id=build_id,
                port=port,
                auto_seed=bool(is_demo and first_run and not params.dry),
                headless=params.headless,
            )
            if params.dry:
                print(f"Service runner dry http://127.0.0.1:{port}/health")
                print(f"Build: {build_id or 'working-copy'}")
                return 0
            if is_demo:
                url = f"http://127.0.0.1:{port}/api/ui/manifest" if params.headless else f"http://127.0.0.1:{port}/"
                demo_provider = _detect_demo_provider(run_path)
                if first_run:
                    print(f"Running {DEMO_NAME}")
                    print(f"Open: {url}")
                    if demo_provider == "openai":
                        print("AI provider: OpenAI")
                    print("Press Ctrl+C to stop")
                    if not params.headless and should_open_url(params.no_open):
                        open_url(url)
                else:
                    print(f"Running {DEMO_NAME} at: {url}")
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
        headless: bool,
        async_runtime: bool | None,
        max_concurrency: int | None,
        cache_size: int | None,
        enable_batching: bool | None,
    ):
        self.app_arg = app_arg
        self.target_raw = target_raw
        self.port = port
        self.build_id = build_id
        self.dry = dry
        self.json_mode = json_mode
        self.no_open = no_open
        self.explain = explain
        self.headless = headless
        self.async_runtime = async_runtime
        self.max_concurrency = max_concurrency
        self.cache_size = cache_size
        self.enable_batching = enable_batching


def _parse_args(args: list[str]) -> _RunParams:
    app_arg = None
    target = None
    port: int | None = None
    build_id = None
    dry = False
    json_mode = False
    no_open = False
    explain = False
    headless = False
    async_runtime: bool | None = None
    max_concurrency: int | None = None
    cache_size: int | None = None
    enable_batching: bool | None = None
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
        if arg == "--headless":
            headless = True
            i += 1
            continue
        if arg == "--async-runtime":
            if i + 1 >= len(args):
                raise Namel3ssError(
                    build_guidance_message(
                        what="--async-runtime flag is missing a value.",
                        why="A boolean value must follow --async-runtime.",
                        fix="Set true or false after the flag.",
                        example="n3 run --async-runtime true",
                    )
                )
            async_runtime = _parse_bool_flag("--async-runtime", args[i + 1])
            i += 2
            continue
        if arg == "--max-concurrency":
            if i + 1 >= len(args):
                raise Namel3ssError(
                    build_guidance_message(
                        what="--max-concurrency flag is missing a value.",
                        why="A positive integer must follow --max-concurrency.",
                        fix="Provide a value like 8.",
                        example="n3 run --max-concurrency 8",
                    )
                )
            try:
                max_concurrency = int(args[i + 1])
            except ValueError as err:
                raise Namel3ssError(
                    build_guidance_message(
                        what="--max-concurrency must be an integer.",
                        why="Concurrency controls require a numeric value.",
                        fix="Set --max-concurrency to a positive integer.",
                        example="n3 run --max-concurrency 8",
                    )
                ) from err
            if max_concurrency < 1:
                raise Namel3ssError("--max-concurrency must be >= 1")
            i += 2
            continue
        if arg == "--cache-size":
            if i + 1 >= len(args):
                raise Namel3ssError(
                    build_guidance_message(
                        what="--cache-size flag is missing a value.",
                        why="A non-negative integer must follow --cache-size.",
                        fix="Provide a value like 128.",
                        example="n3 run --cache-size 128",
                    )
                )
            try:
                cache_size = int(args[i + 1])
            except ValueError as err:
                raise Namel3ssError(
                    build_guidance_message(
                        what="--cache-size must be an integer.",
                        why="Cache size controls require a numeric value.",
                        fix="Set --cache-size to a non-negative integer.",
                        example="n3 run --cache-size 128",
                    )
                ) from err
            if cache_size < 0:
                raise Namel3ssError("--cache-size must be >= 0")
            i += 2
            continue
        if arg == "--enable-batching":
            if i + 1 >= len(args):
                raise Namel3ssError(
                    build_guidance_message(
                        what="--enable-batching flag is missing a value.",
                        why="A boolean value must follow --enable-batching.",
                        fix="Set true or false after the flag.",
                        example="n3 run --enable-batching true",
                    )
                )
            enable_batching = _parse_bool_flag("--enable-batching", args[i + 1])
            i += 2
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
                    why="Supported flags: --target, --port, --build, --dry, --json, --explain, --first-run, --no-open, --headless, --async-runtime, --max-concurrency, --cache-size, --enable-batching.",
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
    return _RunParams(
        app_arg,
        target,
        port,
        build_id,
        dry,
        json_mode,
        no_open,
        explain,
        headless,
        async_runtime,
        max_concurrency,
        cache_size,
        enable_batching,
    )


def _parse_bool_flag(flag: str, raw: str) -> bool:
    token = str(raw).strip().lower()
    if token in {"1", "true", "yes", "on"}:
        return True
    if token in {"0", "false", "no", "off"}:
        return False
    raise Namel3ssError(f"{flag} must be true or false")


def _apply_performance_env_overrides(params: _RunParams) -> None:
    if params.async_runtime is not None:
        os.environ["N3_ASYNC_RUNTIME"] = "true" if params.async_runtime else "false"
    if params.max_concurrency is not None:
        os.environ["N3_MAX_CONCURRENCY"] = str(int(params.max_concurrency))
    if params.cache_size is not None:
        os.environ["N3_CACHE_SIZE"] = str(int(params.cache_size))
    if params.enable_batching is not None:
        os.environ["N3_ENABLE_BATCHING"] = "true" if params.enable_batching else "false"


def _has_performance_overrides(params: _RunParams) -> bool:
    return any(
        value is not None
        for value in (
            params.async_runtime,
            params.max_concurrency,
            params.cache_size,
            params.enable_batching,
        )
    )


def _validate_performance_settings(*, app_path: Path, project_root: Path, force_check: bool) -> None:
    config = load_config(app_path=app_path, root=project_root)
    runtime_config = normalize_performance_runtime_config(config)
    if not runtime_config.enabled and not force_check:
        return
    if force_check and not runtime_config.enabled:
        runtime_config = PerformanceRuntimeConfig(
            enabled=True,
            async_runtime=runtime_config.async_runtime,
            max_concurrency=runtime_config.max_concurrency,
            cache_size=runtime_config.cache_size,
            enable_batching=runtime_config.enable_batching,
            metrics_endpoint=runtime_config.metrics_endpoint,
        )
    program_ir, _sources = load_program(app_path.as_posix())
    require_performance_capability(
        getattr(program_ir, "capabilities", ()),
        runtime_config,
        where="run configuration",
    )


def _print_explain_traces(output: dict) -> None:
    traces = output.get("traces") if isinstance(output, dict) else None
    if not isinstance(traces, list):
        print("Explain traces: none")
        return
    explain_types = {
        TraceEventType.BOUNDARY_START,
        TraceEventType.BOUNDARY_END,
        TraceEventType.EXPRESSION_EXPLAIN,
        TraceEventType.FLOW_START,
        TraceEventType.FLOW_STEP,
        TraceEventType.MUTATION_ALLOWED,
        TraceEventType.MUTATION_BLOCKED,
    }
    explain = [trace for trace in traces if trace.get("type") in explain_types]
    if not explain:
        print("Explain traces: none")
        return
    print("Explain traces:")
    print(dumps_pretty(explain))


def _resolve_run_path(target: str, project_root: Path, app_path: Path, build_id: str | None) -> tuple[Path, str | None]:
    chosen_build = resolve_build_id(project_root, target, build_id)
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
