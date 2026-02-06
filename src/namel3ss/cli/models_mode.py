from __future__ import annotations

from dataclasses import dataclass
import sys

from namel3ss.cli.app_path import resolve_app_path
from namel3ss.cli.text_output import prepare_cli_text
from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.errors.render import format_error
from namel3ss.models import add_registry_entry, deprecate_registry_entry, load_model_registry


@dataclass(frozen=True)
class _Params:
    subcommand: str
    app_arg: str | None
    json_mode: bool
    name: str | None = None
    version: str | None = None
    provider: str | None = None
    domain: str | None = None
    tokens_per_second: float | None = None
    cost_per_token: float | None = None
    privacy_level: str | None = None
    status: str | None = None
    artifact_uri: str | None = None
    training_dataset_version: str | None = None
    metrics: dict[str, float] | None = None


def run_models_command(args: list[str]) -> int:
    try:
        params = _parse_args(args)
        if params.subcommand == "help":
            _print_usage()
            return 0
        app_path = resolve_app_path(params.app_arg)
        project_root = app_path.parent
        if params.subcommand == "list":
            registry = load_model_registry(project_root, app_path)
            payload = {
                "ok": True,
                "count": len(registry.entries),
                "models": [entry.to_dict() for entry in registry.sorted_entries()],
            }
            return _emit(payload, json_mode=params.json_mode)
        if params.subcommand == "add":
            assert params.name and params.version
            assert params.provider and params.domain and params.privacy_level
            assert params.tokens_per_second is not None
            assert params.cost_per_token is not None
            path, entry = add_registry_entry(
                project_root=project_root,
                app_path=app_path,
                name=params.name,
                version=params.version,
                provider=params.provider,
                domain=params.domain,
                tokens_per_second=params.tokens_per_second,
                cost_per_token=params.cost_per_token,
                privacy_level=params.privacy_level,
                status=params.status or "active",
                artifact_uri=params.artifact_uri,
                training_dataset_version=params.training_dataset_version,
                metrics=params.metrics or {},
            )
            payload = {"ok": True, "models_path": path.as_posix(), "model": entry.to_dict()}
            return _emit(payload, json_mode=params.json_mode)
        if params.subcommand == "deprecate":
            assert params.name and params.version
            path, entry = deprecate_registry_entry(
                project_root=project_root,
                app_path=app_path,
                name=params.name,
                version=params.version,
            )
            payload = {"ok": True, "models_path": path.as_posix(), "model": entry.to_dict()}
            return _emit(payload, json_mode=params.json_mode)
        raise Namel3ssError(_unknown_subcommand_message(params.subcommand))
    except Namel3ssError as err:
        print(prepare_cli_text(format_error(err, None)), file=sys.stderr)
        return 1


def _parse_args(args: list[str]) -> _Params:
    if not args or args[0] in {"help", "-h", "--help"}:
        return _Params(subcommand="help", app_arg=None, json_mode=False)
    subcommand = args[0].strip().lower()
    json_mode = False
    provider = None
    domain = None
    privacy_level = None
    status = None
    tokens_per_second = None
    cost_per_token = None
    artifact_uri = None
    training_dataset_version = None
    metrics: dict[str, float] = {}
    positional: list[str] = []
    i = 1
    while i < len(args):
        arg = args[i]
        if arg == "--json":
            json_mode = True
            i += 1
            continue
        if arg in {
            "--provider",
            "--domain",
            "--tokens-per-second",
            "--cost-per-token",
            "--privacy-level",
            "--status",
            "--artifact-uri",
            "--training-dataset-version",
            "--metric",
        }:
            if i + 1 >= len(args):
                raise Namel3ssError(_missing_option_value_message(arg))
            value = args[i + 1]
            if arg == "--provider":
                provider = value
            elif arg == "--domain":
                domain = value
            elif arg == "--tokens-per-second":
                tokens_per_second = _parse_float(value, flag=arg)
            elif arg == "--cost-per-token":
                cost_per_token = _parse_float(value, flag=arg)
            elif arg == "--privacy-level":
                privacy_level = value
            elif arg == "--status":
                status = value
            elif arg == "--artifact-uri":
                artifact_uri = value
            elif arg == "--training-dataset-version":
                training_dataset_version = value
            elif arg == "--metric":
                key, metric = _parse_metric(value)
                metrics[key] = metric
            i += 2
            continue
        if arg.startswith("--"):
            raise Namel3ssError(_unknown_flag_message(arg))
        positional.append(arg)
        i += 1

    if subcommand == "list":
        app_arg = positional[0] if positional else None
        if len(positional) > 1:
            raise Namel3ssError(_too_many_args_message(subcommand))
        return _Params(subcommand=subcommand, app_arg=app_arg, json_mode=json_mode)

    if subcommand == "add":
        if len(positional) < 2:
            raise Namel3ssError(_missing_model_ref_message(subcommand))
        name = positional[0]
        version = positional[1]
        app_arg = positional[2] if len(positional) >= 3 else None
        if len(positional) > 3:
            raise Namel3ssError(_too_many_args_message(subcommand))
        missing_flags = []
        if provider is None:
            missing_flags.append("--provider")
        if domain is None:
            missing_flags.append("--domain")
        if tokens_per_second is None:
            missing_flags.append("--tokens-per-second")
        if cost_per_token is None:
            missing_flags.append("--cost-per-token")
        if privacy_level is None:
            missing_flags.append("--privacy-level")
        if missing_flags:
            raise Namel3ssError(_missing_required_flags_message(missing_flags))
        return _Params(
            subcommand=subcommand,
            app_arg=app_arg,
            json_mode=json_mode,
            name=name,
            version=version,
            provider=provider,
            domain=domain,
            tokens_per_second=tokens_per_second,
            cost_per_token=cost_per_token,
            privacy_level=privacy_level,
            status=status or "active",
            artifact_uri=artifact_uri,
            training_dataset_version=training_dataset_version,
            metrics=metrics,
        )

    if subcommand == "deprecate":
        if len(positional) < 2:
            raise Namel3ssError(_missing_model_ref_message(subcommand))
        name = positional[0]
        version = positional[1]
        app_arg = positional[2] if len(positional) >= 3 else None
        if len(positional) > 3:
            raise Namel3ssError(_too_many_args_message(subcommand))
        return _Params(
            subcommand=subcommand,
            app_arg=app_arg,
            json_mode=json_mode,
            name=name,
            version=version,
        )

    raise Namel3ssError(_unknown_subcommand_message(subcommand))


def _parse_float(value: str, *, flag: str) -> float:
    try:
        parsed = float(value)
    except Exception as err:
        raise Namel3ssError(_invalid_float_message(flag, value)) from err
    if parsed < 0:
        raise Namel3ssError(_invalid_float_message(flag, value))
    return parsed


def _parse_metric(raw: str) -> tuple[str, float]:
    if "=" not in raw:
        raise Namel3ssError(
            build_guidance_message(
                what="Metric format is invalid.",
                why="Metric values must be key=value.",
                fix="Use key=value for each --metric flag.",
                example="--metric accuracy=0.91",
            )
        )
    key, value = raw.split("=", 1)
    metric_key = key.strip()
    if not metric_key:
        raise Namel3ssError(
            build_guidance_message(
                what="Metric key is missing.",
                why="Metric format must include key=value.",
                fix="Set a metric key.",
                example="--metric f1=0.88",
            )
        )
    try:
        parsed = float(value)
    except Exception as err:
        raise Namel3ssError(_invalid_float_message("--metric", raw)) from err
    return metric_key, parsed


def _emit(payload: dict[str, object], *, json_mode: bool) -> int:
    if json_mode:
        print(canonical_json_dumps(payload, pretty=True, drop_run_keys=False))
        return 0 if bool(payload.get("ok")) else 1
    print("Models")
    print(f"  ok: {payload.get('ok')}")
    if "count" in payload:
        print(f"  count: {payload.get('count')}")
    model = payload.get("model")
    if isinstance(model, dict):
        print(f"  model: {model.get('name')}@{model.get('version')} ({model.get('status')})")
    if payload.get("models_path"):
        print(f"  models_path: {payload.get('models_path')}")
    models = payload.get("models")
    if isinstance(models, list):
        for item in models:
            if not isinstance(item, dict):
                continue
            print(
                "  - "
                f"{item.get('name')}@{item.get('version')} "
                f"[{item.get('provider')}, {item.get('domain')}, {item.get('status')}]"
            )
    return 0 if bool(payload.get("ok")) else 1


def _print_usage() -> None:
    print(
        "Usage:\n"
        "  n3 models list [app.ai] [--json]\n"
        "  n3 models add <name> <version> --provider P --domain D --tokens-per-second N --cost-per-token N --privacy-level L [--status active|deprecated] [--training-dataset-version NAME@VERSION] [--artifact-uri URI] [--metric key=value] [app.ai] [--json]\n"
        "  n3 models deprecate <name> <version> [app.ai] [--json]"
    )


def _unknown_subcommand_message(subcommand: str) -> str:
    return build_guidance_message(
        what=f"Unknown models command '{subcommand}'.",
        why="Supported commands are list, add, and deprecate.",
        fix="Use one of the supported subcommands.",
        example="n3 models list",
    )


def _unknown_flag_message(flag: str) -> str:
    return build_guidance_message(
        what=f"Unknown flag '{flag}'.",
        why="This flag is not supported for models commands.",
        fix="Remove the unsupported flag.",
        example="n3 models list",
    )


def _missing_option_value_message(flag: str) -> str:
    return build_guidance_message(
        what=f"Flag '{flag}' is missing a value.",
        why="This option requires a value.",
        fix="Provide a value after the flag.",
        example=f"n3 models add gpt-4 1.0 {flag} value",
    )


def _invalid_float_message(flag: str, raw: str) -> str:
    return build_guidance_message(
        what=f"Flag '{flag}' is invalid.",
        why=f"Could not parse '{raw}' as a non-negative number.",
        fix="Provide a numeric value.",
        example=f"{flag} 10",
    )


def _missing_model_ref_message(subcommand: str) -> str:
    return build_guidance_message(
        what=f"models {subcommand} is missing arguments.",
        why="Model name and version are required.",
        fix="Provide model name and version.",
        example=f"n3 models {subcommand} gpt-4 1.0",
    )


def _too_many_args_message(subcommand: str) -> str:
    return build_guidance_message(
        what=f"models {subcommand} has too many positional arguments.",
        why="Only one optional app path is supported.",
        fix="Remove extra positional values.",
        example=f"n3 models {subcommand} gpt-4 1.0 app.ai",
    )


def _missing_required_flags_message(flags: list[str]) -> str:
    joined = ", ".join(flags)
    return build_guidance_message(
        what="models add is missing required flags.",
        why=f"The following flags are required: {joined}.",
        fix="Provide all required flags.",
        example=(
            "n3 models add gpt-4 1.0 "
            "--provider openai --domain general --tokens-per-second 10 "
            "--cost-per-token 0.00001 --privacy-level standard"
        ),
    )


__all__ = ["run_models_command"]
