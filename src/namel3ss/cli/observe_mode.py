from __future__ import annotations

from dataclasses import dataclass

from namel3ss.config.loader import load_config
from namel3ss.cli.app_path import resolve_app_path
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.observe import filter_events, read_events
from namel3ss.secrets import collect_secret_values, redact_payload, set_audit_root
from namel3ss.utils.json_tools import dumps_pretty


@dataclass
class _ObserveParams:
    app_arg: str | None
    since: str | None
    json_mode: bool


def run_observe_command(args: list[str]) -> int:
    params = _parse_args(args)
    app_path = resolve_app_path(params.app_arg)
    project_root = app_path.parent
    set_audit_root(project_root)
    config = load_config(app_path=app_path, root=project_root)
    events = read_events(project_root)
    filtered = filter_events(events, _parse_duration(params.since) if params.since else None)
    secret_values = collect_secret_values(config)
    filtered = [redact_payload(event, secret_values) for event in filtered]  # type: ignore[assignment]
    payload = {"schema_version": 1, "events": filtered}
    if params.json_mode:
        print(dumps_pretty(payload))
        return 0
    _print_human(filtered)
    return 0


def _parse_args(args: list[str]) -> _ObserveParams:
    app_arg = None
    since = None
    json_mode = False
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--since":
            if i + 1 >= len(args):
                raise Namel3ssError(
                    build_guidance_message(
                        what="--since flag is missing a value.",
                        why="Observe needs a duration like 10m or 2h.",
                        fix="Provide a duration after --since.",
                        example="n3 observe --since 10m",
                    )
                )
            since = args[i + 1]
            i += 2
            continue
        if arg == "--json":
            json_mode = True
            i += 1
            continue
        if arg.startswith("--"):
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Unknown flag '{arg}'.",
                    why="Supported flags: --since, --json.",
                    fix="Remove the unsupported flag.",
                    example="n3 observe --since 10m --json",
                )
            )
        if app_arg is None:
            app_arg = arg
            i += 1
            continue
        raise Namel3ssError(
            build_guidance_message(
                what="Too many positional arguments.",
                why="Observe accepts at most one app path.",
                fix="Provide a single app.ai path or none.",
                example="n3 observe app.ai --since 1h",
            )
        )
    return _ObserveParams(app_arg, since, json_mode)


def _parse_duration(raw: str) -> float:
    if raw is None:
        return 0.0
    text = raw.strip().lower()
    if not text:
        return 0.0
    unit = text[-1]
    number = text[:-1]
    try:
        value = float(number)
    except ValueError as err:
        raise Namel3ssError(
            build_guidance_message(
                what="Duration is invalid.",
                why=f"Could not parse '{raw}'.",
                fix="Use formats like 10m, 2h, 30s, or 1d.",
                example="n3 observe --since 15m",
            )
        ) from err
    scale = {"s": 1, "m": 60, "h": 3600, "d": 86400}.get(unit)
    if scale is None:
        raise Namel3ssError(
            build_guidance_message(
                what="Duration unit is invalid.",
                why=f"Unsupported unit '{unit}'.",
                fix="Use s, m, h, or d.",
                example="n3 observe --since 2h",
            )
        )
    return value * scale


def _print_human(events: list[dict]) -> None:
    if not events:
        print("No events found.")
        return
    for event in events:
        ts = event.get("time") or event.get("time_start")
        kind = event.get("type", "event")
        detail = event.get("flow_name") or event.get("action_id") or event.get("ai_name") or ""
        suffix = f" {detail}" if detail else ""
        print(f"time {ts} {kind}{suffix}")


__all__ = ["run_observe_command"]
