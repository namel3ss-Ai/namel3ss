from __future__ import annotations

from dataclasses import dataclass
import sys

from namel3ss.cli.app_path import resolve_app_path
from namel3ss.cli.text_output import prepare_cli_text
from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.errors.render import format_error
from namel3ss.runtime.ai.model_manager import configure_canary


@dataclass(frozen=True)
class _CanaryParams:
    primary_model: str
    candidate_model: str | None
    fraction: float
    shadow: bool
    app_arg: str | None
    json_mode: bool



def run_model_command(args: list[str]) -> int:
    try:
        if not args or args[0] in {"help", "-h", "--help"}:
            _print_usage()
            return 0
        if args[0] != "canary":
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Unknown model command '{args[0]}'.",
                    why="model supports canary only in this phase.",
                    fix="Use n3 model canary.",
                    example="n3 model canary base candidate 0.1",
                )
            )
        params = _parse_canary_args(args[1:])
        app_path = resolve_app_path(params.app_arg)
        out = configure_canary(
            project_root=app_path.parent,
            app_path=app_path,
            primary_model=params.primary_model,
            candidate_model=params.candidate_model,
            fraction=params.fraction,
            shadow=params.shadow,
        )
        payload = {
            "ok": True,
            "primary_model": params.primary_model,
            "candidate_model": params.candidate_model,
            "fraction": params.fraction,
            "shadow": params.shadow,
            "models_path": out.as_posix(),
        }
        if params.json_mode:
            print(canonical_json_dumps(payload, pretty=True, drop_run_keys=False))
            return 0
        _print_human(payload)
        return 0
    except Namel3ssError as err:
        print(prepare_cli_text(format_error(err, None)), file=sys.stderr)
        return 1



def _parse_canary_args(args: list[str]) -> _CanaryParams:
    json_mode = False
    shadow = False
    filtered: list[str] = []
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--json":
            json_mode = True
            i += 1
            continue
        if arg == "--shadow":
            shadow = True
            i += 1
            continue
        filtered.append(arg)
        i += 1

    if len(filtered) < 2:
        raise Namel3ssError(
            build_guidance_message(
                what="Canary command is missing arguments.",
                why="Need primary model and candidate model.",
                fix="Provide model names and fraction.",
                example="n3 model canary base candidate 0.1",
            )
        )

    primary_model = filtered[0]
    candidate_raw = filtered[1]
    if candidate_raw == "off":
        app_arg = filtered[2] if len(filtered) >= 3 else None
        if len(filtered) > 3:
            raise Namel3ssError(_too_many_args_message())
        return _CanaryParams(
            primary_model=primary_model,
            candidate_model=None,
            fraction=0.0,
            shadow=False,
            app_arg=app_arg,
            json_mode=json_mode,
        )

    if len(filtered) < 3:
        raise Namel3ssError(
            build_guidance_message(
                what="Canary fraction is missing.",
                why="Need a fraction from 0 to 1.",
                fix="Provide a value like 0.1.",
                example="n3 model canary base candidate 0.1",
            )
        )
    try:
        fraction = float(filtered[2])
    except ValueError as err:
        raise Namel3ssError(
            build_guidance_message(
                what="Canary fraction is invalid.",
                why=f"Could not parse '{filtered[2]}'.",
                fix="Use a numeric value from 0 to 1.",
                example="n3 model canary base candidate 0.1",
            )
        ) from err
    if fraction < 0.0 or fraction > 1.0:
        raise Namel3ssError(
            build_guidance_message(
                what="Canary fraction is invalid.",
                why="Fraction must be in range 0 to 1.",
                fix="Use a value like 0.1 for 10%.",
                example="n3 model canary base candidate 0.1",
            )
        )
    app_arg = filtered[3] if len(filtered) >= 4 else None
    if len(filtered) > 4:
        raise Namel3ssError(_too_many_args_message())
    return _CanaryParams(
        primary_model=primary_model,
        candidate_model=candidate_raw,
        fraction=fraction,
        shadow=shadow,
        app_arg=app_arg,
        json_mode=json_mode,
    )



def _too_many_args_message() -> str:
    return build_guidance_message(
        what="Too many positional arguments.",
        why="model canary accepts one optional app path.",
        fix="Provide at most one app.ai path at the end.",
        example="n3 model canary base candidate 0.1 app.ai",
    )



def _print_human(payload: dict[str, object]) -> None:
    print("Model canary configured")
    print(f"  primary: {payload.get('primary_model')}")
    print(f"  candidate: {payload.get('candidate_model')}")
    print(f"  fraction: {payload.get('fraction')}")
    print(f"  shadow: {payload.get('shadow')}")
    print(f"  models_path: {payload.get('models_path')}")



def _print_usage() -> None:
    print(
        "Usage:\n"
        "  n3 model canary <primary_model> <candidate_model> <fraction> [app.ai] [--shadow] [--json]\n"
        "  n3 model canary <primary_model> off [app.ai] [--json]"
    )


__all__ = ["run_model_command"]
