from __future__ import annotations

from dataclasses import dataclass
import sys

from namel3ss.cli.app_path import resolve_app_path
from namel3ss.cli.text_output import prepare_cli_text
from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.errors.render import format_error
from namel3ss.triggers import list_triggers, load_trigger_config, register_trigger, save_trigger_config


@dataclass(frozen=True)
class _TriggerParams:
    subcommand: str
    app_arg: str | None
    json_mode: bool
    trigger_type: str | None
    name: str | None
    pattern: str | None
    flow: str | None


def run_trigger_command(args: list[str]) -> int:
    try:
        params = _parse_args(args)
        if params.subcommand == "help":
            _print_usage()
            return 0
        app_path = resolve_app_path(params.app_arg)
        config = load_trigger_config(app_path.parent, app_path)
        if params.subcommand == "list":
            payload = {
                "ok": True,
                "count": len(config),
                "items": list_triggers(config),
            }
            return _emit(payload, json_mode=params.json_mode)
        if params.subcommand == "register":
            updated = register_trigger(
                config,
                trigger_type=params.trigger_type or "",
                name=params.name or "",
                pattern=params.pattern or "",
                flow=params.flow or "",
                filters=None,
            )
            out_path = save_trigger_config(app_path.parent, app_path, updated)
            payload = {
                "ok": True,
                "action": "register",
                "trigger_type": params.trigger_type,
                "name": params.name,
                "pattern": params.pattern,
                "flow": params.flow,
                "output_path": out_path.as_posix(),
                "count": len(updated),
            }
            return _emit(payload, json_mode=params.json_mode)
        raise Namel3ssError(_unknown_subcommand_message(params.subcommand))
    except Namel3ssError as err:
        print(prepare_cli_text(format_error(err, None)), file=sys.stderr)
        return 1


def _parse_args(args: list[str]) -> _TriggerParams:
    if not args:
        return _TriggerParams(
            subcommand="list",
            app_arg=None,
            json_mode=False,
            trigger_type=None,
            name=None,
            pattern=None,
            flow=None,
        )
    subcommand = str(args[0] or "").strip().lower()
    if subcommand in {"help", "-h", "--help"}:
        return _TriggerParams(
            subcommand="help",
            app_arg=None,
            json_mode=False,
            trigger_type=None,
            name=None,
            pattern=None,
            flow=None,
        )
    json_mode = False
    positional: list[str] = []
    for arg in args[1:]:
        if arg == "--json":
            json_mode = True
            continue
        if arg.startswith("--"):
            raise Namel3ssError(_unknown_flag_message(arg))
        positional.append(arg)
    if subcommand == "list":
        if len(positional) > 1:
            raise Namel3ssError(_too_many_args_message("list"))
        return _TriggerParams(
            subcommand="list",
            app_arg=positional[0] if positional else None,
            json_mode=json_mode,
            trigger_type=None,
            name=None,
            pattern=None,
            flow=None,
        )
    if subcommand == "register":
        if len(positional) < 4:
            raise Namel3ssError(_missing_register_message())
        app_arg = positional[4] if len(positional) >= 5 else None
        if len(positional) > 5:
            raise Namel3ssError(_too_many_args_message("register"))
        return _TriggerParams(
            subcommand="register",
            app_arg=app_arg,
            json_mode=json_mode,
            trigger_type=positional[0],
            name=positional[1],
            pattern=positional[2],
            flow=positional[3],
        )
    raise Namel3ssError(_unknown_subcommand_message(subcommand))


def _emit(payload: dict[str, object], *, json_mode: bool) -> int:
    if json_mode:
        print(canonical_json_dumps(payload, pretty=True, drop_run_keys=False))
        return 0
    if payload.get("action"):
        print(f"Trigger action: {payload.get('action')}")
    print(f"  count: {payload.get('count')}")
    if payload.get("trigger_type"):
        print(f"  type: {payload.get('trigger_type')}")
    if payload.get("name"):
        print(f"  name: {payload.get('name')}")
    if payload.get("pattern"):
        print(f"  pattern: {payload.get('pattern')}")
    if payload.get("flow"):
        print(f"  flow: {payload.get('flow')}")
    if payload.get("output_path"):
        print(f"  output: {payload.get('output_path')}")
    items = payload.get("items")
    if isinstance(items, list):
        for item in items:
            if not isinstance(item, dict):
                continue
            print(
                f"  {item.get('type')} {item.get('name')} "
                f"pattern={item.get('pattern')} flow={item.get('flow')}"
            )
    return 0


def _print_usage() -> None:
    print(
        "Usage:\n"
        "  n3 trigger list [app.ai] [--json]\n"
        "  n3 trigger register <type> <name> <pattern> <flow> [app.ai] [--json]\n"
        "\n"
        "Types:\n"
        "  webhook pattern is path\n"
        "  upload  pattern is directory\n"
        "  timer   pattern is cron\n"
        "  queue   pattern is queue key"
    )


def _unknown_subcommand_message(subcommand: str) -> str:
    return build_guidance_message(
        what=f"Unknown trigger command '{subcommand}'.",
        why="Supported commands are list and register.",
        fix="Use n3 trigger list or n3 trigger register.",
        example="n3 trigger register webhook payment_received /hooks/payment process_payment",
    )


def _unknown_flag_message(flag: str) -> str:
    return build_guidance_message(
        what=f"Unknown flag '{flag}'.",
        why="trigger commands support only --json.",
        fix="Remove unsupported flags.",
        example="n3 trigger list --json",
    )


def _missing_register_message() -> str:
    return build_guidance_message(
        what="trigger register is missing values.",
        why="You must provide type, name, pattern, and flow.",
        fix="Provide all required values in order.",
        example="n3 trigger register webhook payment_received /hooks/payment process_payment",
    )


def _too_many_args_message(subcommand: str) -> str:
    return build_guidance_message(
        what=f"trigger {subcommand} has too many positional arguments.",
        why="Only one optional app path is supported.",
        fix="Pass at most one app.ai path.",
        example=f"n3 trigger {subcommand} app.ai",
    )


__all__ = ["run_trigger_command"]
