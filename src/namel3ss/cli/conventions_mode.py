from __future__ import annotations

from namel3ss.cli.app_path import resolve_app_path
from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.conventions.config import load_conventions_config


def run_conventions_command(args: list[str]) -> int:
    app_arg, remaining = _split_app_arg(args)
    cmd = remaining[0] if remaining else "check"
    tail = remaining[1:] if remaining else []
    if cmd == "check":
        return _check_conventions(app_arg, tail)
    raise Namel3ssError(f"Unknown conventions subcommand '{cmd}'. Supported: check")


def _check_conventions(app_arg: str | None, args: list[str]) -> int:
    json_mode = "--json" in args
    if args and not json_mode:
        raise Namel3ssError("Usage: n3 conventions check [--json]")
    app_path = resolve_app_path(app_arg)
    config = load_conventions_config(app_path.parent, app_path)
    payload = {
        "defaults": {
            "pagination": config.defaults.pagination,
            "page_size_default": config.defaults.page_size_default,
            "page_size_max": config.defaults.page_size_max,
            "filter_fields": list(config.defaults.filter_fields),
        },
        "routes": {
            name: {
                "pagination": entry.pagination,
                "page_size_default": entry.page_size_default,
                "page_size_max": entry.page_size_max,
                "filter_fields": list(entry.filter_fields),
            }
            for name, entry in sorted(config.routes.items())
        },
    }
    if json_mode:
        print(canonical_json_dumps(payload, pretty=True, drop_run_keys=False))
        return 0
    print("Conventions:")
    defaults = payload["defaults"]
    print(
        f"- defaults: pagination={defaults['pagination']} "
        f"page_size_default={defaults['page_size_default']} "
        f"page_size_max={defaults['page_size_max']}"
    )
    if defaults["filter_fields"]:
        print(f"  filter_fields: {', '.join(defaults['filter_fields'])}")
    if not payload["routes"]:
        print("- routes: none")
        return 0
    print("- routes:")
    for name, entry in payload["routes"].items():
        fields = ", ".join(entry.get("filter_fields") or []) or "none"
        print(
            f"  {name}: pagination={entry['pagination']} "
            f"page_size_default={entry['page_size_default']} "
            f"page_size_max={entry['page_size_max']} "
            f"filter_fields={fields}"
        )
    return 0


def _split_app_arg(args: list[str]) -> tuple[str | None, list[str]]:
    if args and args[0].endswith(".ai"):
        return args[0], args[1:]
    return None, args


def _missing_conventions_message() -> str:
    return build_guidance_message(
        what="Conventions config is missing.",
        why="The conventions.yaml file could not be loaded.",
        fix="Create the file or run n3 conventions check.",
        example="n3 conventions check",
    )


__all__ = ["run_conventions_command"]
