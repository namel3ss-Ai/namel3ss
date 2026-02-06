from __future__ import annotations

from dataclasses import dataclass
import sys

from namel3ss.cli.app_path import resolve_app_path
from namel3ss.cli.text_output import prepare_cli_text
from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.errors.render import format_error
from namel3ss.mlops import get_mlops_client
from namel3ss.retrain import list_retrain_jobs, run_retrain_job, schedule_retrain_jobs, write_retrain_payload


@dataclass(frozen=True)
class _RetrainParams:
    subcommand: str
    app_arg: str | None
    json_mode: bool
    job_id: str | None = None


def run_retrain_command(args: list[str]) -> int:
    try:
        params = _parse_args(args)
        if params.subcommand == "help":
            _print_usage()
            return 0

        app_path = resolve_app_path(params.app_arg)
        project_root = app_path.parent

        if params.subcommand == "schedule":
            payload = schedule_retrain_jobs(project_root, app_path)
            output_path = write_retrain_payload(project_root, app_path)
            payload["output_path"] = output_path.as_posix()
            client = get_mlops_client(project_root, app_path, required=False)
            if client is not None:
                payload["mlops"] = client.log_retrain_experiments(payload)
            if params.json_mode:
                print(canonical_json_dumps(payload, pretty=True, drop_run_keys=False))
                return 0
            _print_schedule(payload)
            return 0

        if params.subcommand == "list":
            jobs = list_retrain_jobs(project_root, app_path)
            payload = {"ok": True, "count": len(jobs), "jobs": jobs}
            if params.json_mode:
                print(canonical_json_dumps(payload, pretty=True, drop_run_keys=False))
                return 0
            _print_jobs(jobs)
            return 0

        if params.subcommand == "run":
            payload = run_retrain_job(project_root, app_path, job_id=params.job_id or "")
            if params.json_mode:
                print(canonical_json_dumps(payload, pretty=True, drop_run_keys=False))
                return 0
            _print_run(payload)
            return 0

        raise Namel3ssError(_unknown_subcommand_message(params.subcommand))
    except Namel3ssError as err:
        print(prepare_cli_text(format_error(err, None)), file=sys.stderr)
        return 1


def _parse_args(args: list[str]) -> _RetrainParams:
    if not args or args[0] in {"help", "-h", "--help"}:
        return _RetrainParams(subcommand="help", app_arg=None, json_mode=False)
    subcommand = str(args[0]).strip().lower()
    if subcommand == "schedule":
        app_arg, json_mode = _parse_single_app_args(args[1:], command="schedule")
        return _RetrainParams(subcommand=subcommand, app_arg=app_arg, json_mode=json_mode)
    if subcommand == "list":
        app_arg, json_mode = _parse_single_app_args(args[1:], command="list")
        return _RetrainParams(subcommand=subcommand, app_arg=app_arg, json_mode=json_mode)
    if subcommand == "run":
        return _parse_run_args(args[1:])
    raise Namel3ssError(_unknown_subcommand_message(subcommand))


def _parse_single_app_args(args: list[str], *, command: str) -> tuple[str | None, bool]:
    app_arg = None
    json_mode = False
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--json":
            json_mode = True
            i += 1
            continue
        if arg.startswith("--"):
            raise Namel3ssError(_unknown_flag_message(arg, command=command))
        if app_arg is None:
            app_arg = arg
            i += 1
            continue
        raise Namel3ssError(_too_many_args_message(command))
    return app_arg, json_mode


def _parse_run_args(args: list[str]) -> _RetrainParams:
    json_mode = False
    positional: list[str] = []
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--json":
            json_mode = True
            i += 1
            continue
        if arg.startswith("--"):
            raise Namel3ssError(_unknown_flag_message(arg, command="run"))
        positional.append(arg)
        i += 1
    if not positional:
        raise Namel3ssError(_missing_job_message())
    job_id = positional[0]
    app_arg = positional[1] if len(positional) >= 2 else None
    if len(positional) > 2:
        raise Namel3ssError(_too_many_args_message("run"))
    return _RetrainParams(subcommand="run", app_arg=app_arg, json_mode=json_mode, job_id=job_id)


def _print_schedule(payload: dict[str, object]) -> None:
    print("Retrain schedule")
    output_path = payload.get("output_path")
    if output_path:
        print(f"  output: {output_path}")
    jobs_path = payload.get("jobs_path")
    if jobs_path:
        print(f"  jobs: {jobs_path}")
    print(f"  scheduled_jobs: {payload.get('scheduled_count', 0)}")
    suggestions = payload.get("suggestions")
    if not isinstance(suggestions, list) or not suggestions:
        print("  suggestions: none")
        return
    print(f"  suggestions: {len(suggestions)}")
    for entry in suggestions:
        if not isinstance(entry, dict):
            continue
        print(f"  model={entry.get('model_name')} reason={entry.get('reason')}")


def _print_jobs(jobs: list[dict[str, object]]) -> None:
    if not jobs:
        print("No retrain jobs scheduled.")
        return
    print("Retrain jobs")
    for job in jobs:
        print(
            "  "
            f"id={job.get('job_id')} model={job.get('model_name')} target={job.get('target_version')} "
            f"status={job.get('status')} backend={job.get('backend')}"
        )


def _print_run(payload: dict[str, object]) -> None:
    print("Retrain run")
    print(f"  ok: {payload.get('ok')}")
    job = payload.get("job")
    if isinstance(job, dict):
        print(
            "  "
            f"id={job.get('job_id')} model={job.get('model_name')} target={job.get('target_version')} status={job.get('status')}"
        )
        if job.get("result_uri"):
            print(f"  result_uri: {job.get('result_uri')}")
    mlops = payload.get("mlops")
    if isinstance(mlops, dict):
        print(f"  mlops_queued: {mlops.get('queued')}")


def _print_usage() -> None:
    print(
        "Usage:\n"
        "  n3 retrain schedule [app.ai] [--json]\n"
        "  n3 retrain list [app.ai] [--json]\n"
        "  n3 retrain run <job_id> [app.ai] [--json]"
    )


def _unknown_subcommand_message(subcommand: str) -> str:
    return build_guidance_message(
        what=f"Unknown retrain command '{subcommand}'.",
        why="retrain supports schedule, list, and run.",
        fix="Use one of the supported retrain subcommands.",
        example="n3 retrain list --json",
    )


def _unknown_flag_message(flag: str, *, command: str) -> str:
    return build_guidance_message(
        what=f"Unknown flag '{flag}'.",
        why=f"retrain {command} supports --json only.",
        fix="Remove the unsupported flag.",
        example=f"n3 retrain {command} --json",
    )


def _missing_job_message() -> str:
    return build_guidance_message(
        what="retrain run is missing job id.",
        why="run requires a scheduled job id.",
        fix="List jobs and provide one id.",
        example="n3 retrain run job-000001",
    )


def _too_many_args_message(command: str) -> str:
    return build_guidance_message(
        what=f"retrain {command} has too many positional arguments.",
        why="Only one optional app path is supported.",
        fix="Remove extra positional values.",
        example=f"n3 retrain {command} app.ai",
    )


__all__ = ["run_retrain_command"]
