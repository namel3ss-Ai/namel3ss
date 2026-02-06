from __future__ import annotations

from dataclasses import dataclass
import sys

from namel3ss.cli.app_path import resolve_app_path
from namel3ss.cli.text_output import prepare_cli_text
from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.errors.render import format_error
from namel3ss.observability.trace_runs import latest_trace_run_id, list_trace_runs, read_trace_entries


@dataclass(frozen=True)
class _TraceParams:
    subcommand: str
    app_arg: str | None
    run_id: str | None
    json_mode: bool


def run_trace_command(args: list[str]) -> int:
    try:
        params = _parse_args(args)
        if params.subcommand == "help":
            _print_usage()
            return 0
        app_path = resolve_app_path(params.app_arg)
        project_root = app_path.parent
        if params.subcommand == "list":
            runs = list_trace_runs(project_root, app_path)
            payload = {"ok": True, "count": len(runs), "runs": runs}
            return _emit(payload, json_mode=params.json_mode)
        if params.subcommand == "show":
            run_id = str(params.run_id or "").strip()
            if run_id == "latest":
                latest = latest_trace_run_id(project_root, app_path)
                if not latest:
                    payload = {"ok": False, "error": "No trace runs were found.", "kind": "engine"}
                    return _emit(payload, json_mode=params.json_mode)
                run_id = latest
            entries = read_trace_entries(project_root, app_path, run_id)
            if not entries:
                payload = {"ok": False, "error": f'Trace run "{run_id}" was not found.', "kind": "engine"}
                return _emit(payload, json_mode=params.json_mode)
            payload = {"ok": True, "run_id": run_id, "count": len(entries), "trace": entries}
            return _emit(payload, json_mode=params.json_mode)
        raise Namel3ssError(_unknown_subcommand_message(params.subcommand))
    except Namel3ssError as err:
        print(prepare_cli_text(format_error(err, None)), file=sys.stderr)
        return 1


def _parse_args(args: list[str]) -> _TraceParams:
    if not args or args[0] in {"help", "-h", "--help"}:
        return _TraceParams(subcommand="help", app_arg=None, run_id=None, json_mode=False)
    subcommand = args[0].strip().lower()
    json_mode = False
    positional: list[str] = []
    i = 1
    while i < len(args):
        arg = args[i]
        if arg == "--json":
            json_mode = True
            i += 1
            continue
        if arg.startswith("--"):
            raise Namel3ssError(_unknown_flag_message(arg))
        positional.append(arg)
        i += 1
    if subcommand == "list":
        if len(positional) > 1:
            raise Namel3ssError(_too_many_args_message("list"))
        app_arg = positional[0] if positional else None
        return _TraceParams(subcommand=subcommand, app_arg=app_arg, run_id=None, json_mode=json_mode)
    if subcommand == "show":
        if not positional:
            raise Namel3ssError(_missing_run_id_message())
        run_id = positional[0]
        if len(positional) > 2:
            raise Namel3ssError(_too_many_args_message("show"))
        app_arg = positional[1] if len(positional) == 2 else None
        return _TraceParams(subcommand=subcommand, app_arg=app_arg, run_id=run_id, json_mode=json_mode)
    raise Namel3ssError(_unknown_subcommand_message(subcommand))


def _emit(payload: dict[str, object], *, json_mode: bool) -> int:
    ok = bool(payload.get("ok"))
    if json_mode:
        print(canonical_json_dumps(payload, pretty=True, drop_run_keys=False))
        return 0 if ok else 1
    print("Traces")
    print(f"  ok: {ok}")
    if payload.get("run_id"):
        print(f"  run_id: {payload.get('run_id')}")
    if "count" in payload:
        print(f"  count: {payload.get('count')}")
    runs = payload.get("runs")
    if isinstance(runs, list):
        for item in runs:
            if not isinstance(item, dict):
                continue
            print(
                "  - "
                f"{item.get('run_id')} "
                f"{item.get('flow_name')} "
                f"steps={item.get('step_count')} errors={item.get('error_count')}"
            )
    trace = payload.get("trace")
    if isinstance(trace, list):
        for item in trace:
            if not isinstance(item, dict):
                continue
            print(
                "  - "
                f"{item.get('step_id')} "
                f"{item.get('step_name')} "
                f"t={item.get('timestamp')} "
                f"ms={item.get('duration_ms')}"
            )
    if payload.get("error"):
        print(f"  error: {payload.get('error')}")
    return 0 if ok else 1


def _print_usage() -> None:
    print(
        "Usage:\n"
        "  n3 trace list [app.ai] [--json]\n"
        "  n3 trace show <run_id|latest> [app.ai] [--json]"
    )


def _unknown_subcommand_message(subcommand: str) -> str:
    return build_guidance_message(
        what=f"Unknown trace command '{subcommand}'.",
        why="Supported commands are list and show.",
        fix="Use a supported subcommand.",
        example="n3 trace list",
    )


def _unknown_flag_message(flag: str) -> str:
    return build_guidance_message(
        what=f"Unknown flag '{flag}'.",
        why="trace supports only --json.",
        fix="Remove the unsupported flag.",
        example="n3 trace list --json",
    )


def _missing_run_id_message() -> str:
    return build_guidance_message(
        what="Trace run id is missing.",
        why="trace show requires a run id or latest.",
        fix="Provide a run id from n3 trace list.",
        example="n3 trace show latest",
    )


def _too_many_args_message(subcommand: str) -> str:
    return build_guidance_message(
        what=f"trace {subcommand} has too many positional arguments.",
        why="Only one optional app path is supported.",
        fix="Remove extra positional values.",
        example=f"n3 trace {subcommand}",
    )


__all__ = ["run_trace_command"]
