from __future__ import annotations

from dataclasses import dataclass
import sys

from namel3ss.cli.app_path import resolve_app_path
from namel3ss.cli.text_output import prepare_cli_text
from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.errors.render import format_error
from namel3ss.observability.otlp_exporter import export_trace_runs


@dataclass(frozen=True)
class _ExportParams:
    kind: str
    app_arg: str | None
    run_ids: tuple[str, ...]
    json_mode: bool


def run_export_command(args: list[str]) -> int:
    try:
        params = _parse_args(args)
        if params.kind == "help":
            _print_usage()
            return 0
        app_path = resolve_app_path(params.app_arg)
        if params.kind != "traces":
            raise Namel3ssError(_unknown_kind_message(params.kind))
        payload = export_trace_runs(
            project_root=app_path.parent,
            app_path=app_path,
            run_ids=list(params.run_ids) or None,
        )
        return _emit(payload, json_mode=params.json_mode)
    except Namel3ssError as err:
        print(prepare_cli_text(format_error(err, None)), file=sys.stderr)
        return 1


def _parse_args(args: list[str]) -> _ExportParams:
    if not args or args[0] in {"help", "-h", "--help"}:
        return _ExportParams(kind="help", app_arg=None, run_ids=(), json_mode=False)
    kind = args[0].strip().lower()
    json_mode = False
    run_ids: list[str] = []
    positional: list[str] = []
    i = 1
    while i < len(args):
        arg = args[i]
        if arg == "--json":
            json_mode = True
            i += 1
            continue
        if arg == "--run-id":
            if i + 1 >= len(args):
                raise Namel3ssError(_missing_flag_value_message("--run-id"))
            run_ids.append(args[i + 1])
            i += 2
            continue
        if arg.startswith("--"):
            raise Namel3ssError(_unknown_flag_message(arg))
        positional.append(arg)
        i += 1
    if len(positional) > 1:
        raise Namel3ssError(_too_many_args_message())
    app_arg = positional[0] if positional else None
    return _ExportParams(kind=kind, app_arg=app_arg, run_ids=tuple(run_ids), json_mode=json_mode)


def _emit(payload: dict[str, object], *, json_mode: bool) -> int:
    if json_mode:
        print(canonical_json_dumps(payload, pretty=True, drop_run_keys=False))
        return 0 if bool(payload.get("ok")) else 1
    print("Export")
    print(f"  ok: {payload.get('ok')}")
    print(f"  endpoint: {payload.get('endpoint')}")
    print(f"  runs: {payload.get('runs')}")
    print(f"  exported_spans: {payload.get('exported_spans')}")
    print(f"  failed_batches: {payload.get('failed_batches')}")
    return 0 if bool(payload.get("ok")) else 1


def _print_usage() -> None:
    print(
        "Usage:\n"
        "  n3 export traces [app.ai] [--run-id <id>]... [--json]"
    )


def _unknown_kind_message(kind: str) -> str:
    return build_guidance_message(
        what=f"Unknown export kind '{kind}'.",
        why="Only traces export is supported.",
        fix="Use export traces.",
        example="n3 export traces",
    )


def _unknown_flag_message(flag: str) -> str:
    return build_guidance_message(
        what=f"Unknown flag '{flag}'.",
        why="export traces supports --run-id and --json.",
        fix="Remove the unsupported flag.",
        example="n3 export traces --json",
    )


def _missing_flag_value_message(flag: str) -> str:
    return build_guidance_message(
        what=f"{flag} flag is missing a value.",
        why="A run id is required after this flag.",
        fix="Provide a trace run id.",
        example="n3 export traces --run-id demo-000001",
    )


def _too_many_args_message() -> str:
    return build_guidance_message(
        what="export traces has too many positional arguments.",
        why="Only one optional app path is supported.",
        fix="Remove extra positional values.",
        example="n3 export traces app.ai",
    )


__all__ = ["run_export_command"]
