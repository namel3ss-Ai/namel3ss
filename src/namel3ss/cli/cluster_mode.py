from __future__ import annotations

from dataclasses import dataclass
import sys

from namel3ss.cli.app_path import resolve_app_path
from namel3ss.cli.text_output import prepare_cli_text
from namel3ss.cluster import cluster_status, deploy_cluster, scale_cluster
from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.errors.render import format_error


@dataclass(frozen=True)
class _ClusterParams:
    subcommand: str
    app_arg: str | None
    json_mode: bool
    cpu_percent: float | None = None
    version: str | None = None


def run_cluster_command(args: list[str]) -> int:
    try:
        params = _parse_args(args)
        if params.subcommand == "help":
            _print_usage()
            return 0
        app_path = resolve_app_path(params.app_arg)
        project_root = app_path.parent
        if params.subcommand == "status":
            payload = cluster_status(project_root, app_path)
            return _emit(payload, json_mode=params.json_mode)
        if params.subcommand == "scale":
            assert params.cpu_percent is not None
            payload = scale_cluster(project_root=project_root, app_path=app_path, cpu_percent=params.cpu_percent)
            return _emit(payload, json_mode=params.json_mode)
        if params.subcommand == "deploy":
            assert params.version
            payload = deploy_cluster(project_root=project_root, app_path=app_path, version=params.version)
            return _emit(payload, json_mode=params.json_mode)
        raise Namel3ssError(_unknown_subcommand_message(params.subcommand))
    except Namel3ssError as err:
        print(prepare_cli_text(format_error(err, None)), file=sys.stderr)
        return 1


def _parse_args(args: list[str]) -> _ClusterParams:
    if not args or args[0] in {"help", "--help", "-h"}:
        return _ClusterParams(subcommand="help", app_arg=None, json_mode=False)
    subcommand = str(args[0] or "").strip().lower()
    json_mode = False
    positional: list[str] = []
    idx = 1
    while idx < len(args):
        arg = args[idx]
        if arg == "--json":
            json_mode = True
            idx += 1
            continue
        if arg.startswith("--"):
            raise Namel3ssError(_unknown_flag_message(arg))
        positional.append(arg)
        idx += 1
    if subcommand == "status":
        app_arg = positional[0] if positional else None
        if len(positional) > 1:
            raise Namel3ssError(_too_many_args_message(subcommand))
        return _ClusterParams(subcommand=subcommand, app_arg=app_arg, json_mode=json_mode)
    if subcommand == "scale":
        if not positional:
            raise Namel3ssError(_missing_scale_value_message())
        cpu_percent = _parse_float(positional[0], flag="cpu_percent")
        app_arg = positional[1] if len(positional) >= 2 else None
        if len(positional) > 2:
            raise Namel3ssError(_too_many_args_message(subcommand))
        return _ClusterParams(subcommand=subcommand, app_arg=app_arg, json_mode=json_mode, cpu_percent=cpu_percent)
    if subcommand == "deploy":
        if not positional:
            raise Namel3ssError(_missing_deploy_version_message())
        version = positional[0]
        app_arg = positional[1] if len(positional) >= 2 else None
        if len(positional) > 2:
            raise Namel3ssError(_too_many_args_message(subcommand))
        return _ClusterParams(subcommand=subcommand, app_arg=app_arg, json_mode=json_mode, version=version)
    raise Namel3ssError(_unknown_subcommand_message(subcommand))


def _parse_float(value: str, *, flag: str) -> float:
    try:
        parsed = float(value)
    except Exception as err:
        raise Namel3ssError(_invalid_number_message(flag, value)) from err
    if parsed < 0:
        raise Namel3ssError(_invalid_number_message(flag, value))
    return parsed


def _emit(payload: dict[str, object], *, json_mode: bool) -> int:
    if json_mode:
        print(canonical_json_dumps(payload, pretty=True, drop_run_keys=False))
        return 0 if bool(payload.get("ok")) else 1
    print("Cluster")
    print(f"  ok: {payload.get('ok')}")
    if payload.get("action"):
        print(f"  action: {payload.get('action')} ({payload.get('reason')})")
    if "active_nodes" in payload:
        print(f"  active_nodes: {payload.get('active_nodes')}")
    if "worker_count" in payload:
        print(f"  worker_count: {payload.get('worker_count')}")
    if "from_nodes" in payload and "to_nodes" in payload:
        print(f"  nodes: {payload.get('from_nodes')} -> {payload.get('to_nodes')}")
    if payload.get("deployed_version"):
        print(f"  deployed_version: {payload.get('deployed_version')}")
    if payload.get("event_count") is not None:
        print(f"  event_count: {payload.get('event_count')}")
    event = payload.get("event")
    if isinstance(event, dict):
        print(f"  event: {event.get('action')} node={event.get('node_name')} step={event.get('step_count')}")
    steps = payload.get("rollout_steps")
    if isinstance(steps, list):
        print(f"  rollout_steps: {len(steps)}")
    nodes = payload.get("nodes")
    if isinstance(nodes, list):
        for node in nodes:
            if not isinstance(node, dict):
                continue
            print(
                f"  - {node.get('name')} role={node.get('role')} "
                f"host={node.get('host')} status={node.get('status')}"
            )
    return 0 if bool(payload.get("ok")) else 1


def _print_usage() -> None:
    print(
        "Usage:\n"
        "  n3 cluster status [app.ai] [--json]\n"
        "  n3 cluster scale <cpu_percent> [app.ai] [--json]\n"
        "  n3 cluster deploy <version> [app.ai] [--json]"
    )


def _unknown_subcommand_message(subcommand: str) -> str:
    return build_guidance_message(
        what=f"Unknown cluster command '{subcommand}'.",
        why="Supported commands are status, scale, and deploy.",
        fix="Use one of the supported cluster subcommands.",
        example="n3 cluster status",
    )


def _unknown_flag_message(flag: str) -> str:
    return build_guidance_message(
        what=f"Unknown flag '{flag}'.",
        why="cluster commands support only --json.",
        fix="Remove unsupported flags.",
        example="n3 cluster status --json",
    )


def _too_many_args_message(subcommand: str) -> str:
    return build_guidance_message(
        what=f"cluster {subcommand} has too many positional arguments.",
        why="Only one optional app path is supported.",
        fix="Pass at most one app.ai path.",
        example=f"n3 cluster {subcommand} app.ai",
    )


def _missing_scale_value_message() -> str:
    return build_guidance_message(
        what="cluster scale is missing cpu_percent.",
        why="scale needs a CPU percentage input.",
        fix="Provide cpu_percent as the first argument.",
        example="n3 cluster scale 85",
    )


def _missing_deploy_version_message() -> str:
    return build_guidance_message(
        what="cluster deploy is missing version.",
        why="deploy needs a version string.",
        fix="Provide a version after cluster deploy.",
        example="n3 cluster deploy 1.2.0",
    )


def _invalid_number_message(flag: str, value: str) -> str:
    return build_guidance_message(
        what=f"{flag} value '{value}' is invalid.",
        why="Expected a non-negative number.",
        fix="Provide a valid number.",
        example="n3 cluster scale 70",
    )


__all__ = ["run_cluster_command"]
