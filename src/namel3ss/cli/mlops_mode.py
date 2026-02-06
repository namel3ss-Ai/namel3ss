from __future__ import annotations

from dataclasses import dataclass
import hashlib
import sys

from namel3ss.cli.app_path import resolve_app_path
from namel3ss.cli.text_output import prepare_cli_text
from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.errors.render import format_error
from namel3ss.mlops import get_mlops_client
from namel3ss.mlops.quality_gate import validate_model_registration
from namel3ss.runtime.capabilities.feature_gate import require_app_capability


@dataclass(frozen=True)
class _MLOpsParams:
    subcommand: str
    name: str | None
    version: str | None
    app_arg: str | None
    json_mode: bool
    artifact_uri: str | None
    experiment_id: str | None
    stage: str | None
    dataset: str | None
    metrics: dict[str, float]


def run_mlops_command(args: list[str]) -> int:
    try:
        params = _parse_args(args)
        if params.subcommand == "help":
            _print_usage()
            return 0

        app_path = resolve_app_path(params.app_arg)
        require_app_capability(app_path, "versioning_quality_mlops")
        source = app_path.read_text(encoding="utf-8")

        if params.subcommand == "register-model":
            validate_model_registration(
                source=source,
                project_root=app_path.parent,
                app_path=app_path,
            )
            client = get_mlops_client(app_path.parent, app_path, required=True)
            assert client is not None
            experiment_id = params.experiment_id or _default_experiment_id(params.name or "", params.version or "")
            payload = client.register_model(
                name=params.name or "",
                version=params.version or "",
                artifact_uri=params.artifact_uri or "",
                metrics=params.metrics,
                experiment_id=experiment_id,
                stage=params.stage,
                dataset=params.dataset,
            )
            payload["quality_ok"] = True
            return _emit(payload, json_mode=params.json_mode)

        if params.subcommand == "get-model":
            client = get_mlops_client(app_path.parent, app_path, required=True)
            assert client is not None
            payload = client.get_model(name=params.name or "", version=params.version or "")
            return _emit(payload, json_mode=params.json_mode)

        if params.subcommand == "list-models":
            client = get_mlops_client(app_path.parent, app_path, required=True)
            assert client is not None
            payload = client.list_models()
            return _emit(payload, json_mode=params.json_mode)

        raise Namel3ssError(_unknown_subcommand_message(params.subcommand))
    except Namel3ssError as err:
        print(prepare_cli_text(format_error(err, None)), file=sys.stderr)
        return 1


def _parse_args(args: list[str]) -> _MLOpsParams:
    if not args:
        return _MLOpsParams(
            subcommand="help",
            name=None,
            version=None,
            app_arg=None,
            json_mode=False,
            artifact_uri=None,
            experiment_id=None,
            stage=None,
            dataset=None,
            metrics={},
        )

    subcommand = args[0].strip().lower()
    if subcommand in {"help", "-h", "--help"}:
        return _MLOpsParams(
            subcommand="help",
            name=None,
            version=None,
            app_arg=None,
            json_mode=False,
            artifact_uri=None,
            experiment_id=None,
            stage=None,
            dataset=None,
            metrics={},
        )

    json_mode = False
    artifact_uri = None
    experiment_id = None
    stage = None
    dataset = None
    metrics: dict[str, float] = {}
    positional: list[str] = []

    idx = 1
    while idx < len(args):
        arg = args[idx]
        if arg == "--json":
            json_mode = True
            idx += 1
            continue
        if arg in {"--artifact-uri", "--experiment-id", "--stage", "--dataset", "--metric"}:
            if idx + 1 >= len(args):
                raise Namel3ssError(_missing_option_value_message(arg))
            value = args[idx + 1]
            if arg == "--artifact-uri":
                artifact_uri = value
            elif arg == "--experiment-id":
                experiment_id = value
            elif arg == "--stage":
                stage = value
            elif arg == "--dataset":
                dataset = value
            elif arg == "--metric":
                key, parsed = _parse_metric(value)
                metrics[key] = parsed
            idx += 2
            continue
        if arg.startswith("--"):
            raise Namel3ssError(_unknown_flag_message(arg))
        positional.append(arg)
        idx += 1

    if subcommand == "register-model":
        if len(positional) < 2:
            raise Namel3ssError(_missing_name_version_message(subcommand))
        name = positional[0]
        version = positional[1]
        app_arg = positional[2] if len(positional) >= 3 else None
        if len(positional) > 3:
            raise Namel3ssError(_too_many_args_message(subcommand))
        if not artifact_uri:
            raise Namel3ssError(_missing_required_flag_message("--artifact-uri"))
        return _MLOpsParams(
            subcommand=subcommand,
            name=name,
            version=version,
            app_arg=app_arg,
            json_mode=json_mode,
            artifact_uri=artifact_uri,
            experiment_id=experiment_id,
            stage=stage,
            dataset=dataset,
            metrics=metrics,
        )

    if subcommand == "get-model":
        if len(positional) < 2:
            raise Namel3ssError(_missing_name_version_message(subcommand))
        name = positional[0]
        version = positional[1]
        app_arg = positional[2] if len(positional) >= 3 else None
        if len(positional) > 3:
            raise Namel3ssError(_too_many_args_message(subcommand))
        return _MLOpsParams(
            subcommand=subcommand,
            name=name,
            version=version,
            app_arg=app_arg,
            json_mode=json_mode,
            artifact_uri=None,
            experiment_id=experiment_id,
            stage=stage,
            dataset=dataset,
            metrics=metrics,
        )

    if subcommand == "list-models":
        if artifact_uri or experiment_id or stage or dataset or metrics:
            raise Namel3ssError(
                build_guidance_message(
                    what="mlops list-models does not accept model options.",
                    why="list-models only accepts one optional app path and --json.",
                    fix="Remove model flags from the command.",
                    example="n3 mlops list-models --json",
                )
            )
        app_arg = positional[0] if positional else None
        if len(positional) > 1:
            raise Namel3ssError(_too_many_args_message(subcommand))
        return _MLOpsParams(
            subcommand=subcommand,
            name=None,
            version=None,
            app_arg=app_arg,
            json_mode=json_mode,
            artifact_uri=None,
            experiment_id=None,
            stage=None,
            dataset=None,
            metrics={},
        )

    raise Namel3ssError(_unknown_subcommand_message(subcommand))


def _parse_metric(raw: str) -> tuple[str, float]:
    if "=" not in raw:
        raise Namel3ssError(
            build_guidance_message(
                what="Metric format is invalid.",
                why="Metrics must be key=value.",
                fix="Use --metric accuracy=0.91 format.",
                example="n3 mlops register-model base 1.0 --artifact-uri uri --metric accuracy=0.91",
            )
        )
    key, value = raw.split("=", 1)
    metric_key = key.strip()
    if not metric_key:
        raise Namel3ssError(_metric_key_missing_message())
    try:
        metric_value = float(value)
    except Exception as err:
        raise Namel3ssError(_metric_value_invalid_message(raw)) from err
    return metric_key, metric_value


def _emit(payload: dict[str, object], *, json_mode: bool) -> int:
    if json_mode:
        print(canonical_json_dumps(payload, pretty=True, drop_run_keys=False))
        return 0 if bool(payload.get("ok", False)) else 1
    print("MLOps")
    print(f"  ok: {payload.get('ok')}")
    if "count" in payload:
        print(f"  count: {payload.get('count')}")
    if "queued" in payload:
        print(f"  queued: {payload.get('queued')}")
    model = payload.get("model")
    if isinstance(model, dict):
        print(f"  model: {model.get('name')}@{model.get('version')}")
    models = payload.get("models")
    if isinstance(models, list):
        for item in models:
            if not isinstance(item, dict):
                continue
            print(f"  - {item.get('name')}@{item.get('version')} stage={item.get('stage')}")
    if payload.get("error"):
        print(f"  error: {payload.get('error')}")
    return 0 if bool(payload.get("ok", False)) else 1


def _default_experiment_id(name: str, version: str) -> str:
    payload = f"{name}|{version}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:12]


def _print_usage() -> None:
    print(
        "Usage:\n"
        "  n3 mlops register-model <name> <version> --artifact-uri URI [--metric key=value] [--experiment-id ID] [--stage STAGE] [--dataset NAME] [app.ai] [--json]\n"
        "  n3 mlops get-model <name> <version> [app.ai] [--json]\n"
        "  n3 mlops list-models [app.ai] [--json]"
    )


def _unknown_subcommand_message(subcommand: str) -> str:
    return build_guidance_message(
        what=f"Unknown mlops command '{subcommand}'.",
        why="Supported commands are register-model, get-model, and list-models.",
        fix="Use one of the supported subcommands.",
        example="n3 mlops get-model base 1.0",
    )


def _unknown_flag_message(flag: str) -> str:
    return build_guidance_message(
        what=f"Unknown flag '{flag}'.",
        why="This flag is not supported for mlops commands.",
        fix="Remove the unsupported flag.",
        example="n3 mlops help",
    )


def _missing_option_value_message(flag: str) -> str:
    return build_guidance_message(
        what=f"Flag '{flag}' is missing a value.",
        why="This option requires a value.",
        fix="Provide a value for the option.",
        example=f"n3 mlops register-model base 1.0 {flag} value",
    )


def _missing_required_flag_message(flag: str) -> str:
    return build_guidance_message(
        what=f"Required flag '{flag}' is missing.",
        why="register-model needs an artifact URI.",
        fix=f"Add {flag} to the command.",
        example="n3 mlops register-model base 1.0 --artifact-uri model://base/1.0",
    )


def _missing_name_version_message(subcommand: str) -> str:
    return build_guidance_message(
        what=f"mlops {subcommand} is missing arguments.",
        why="Model name and version are required.",
        fix="Provide model name and version.",
        example=f"n3 mlops {subcommand} base 1.0",
    )


def _too_many_args_message(subcommand: str) -> str:
    return build_guidance_message(
        what=f"mlops {subcommand} has too many positional arguments.",
        why="Only one optional app path is supported.",
        fix="Remove extra positional values.",
        example=f"n3 mlops {subcommand} base 1.0 app.ai",
    )


def _metric_key_missing_message() -> str:
    return build_guidance_message(
        what="Metric key is missing.",
        why="Metric values must use key=value.",
        fix="Set a metric key.",
        example="--metric accuracy=0.91",
    )


def _metric_value_invalid_message(raw: str) -> str:
    return build_guidance_message(
        what="Metric value is invalid.",
        why=f"Could not parse metric '{raw}'.",
        fix="Use numeric values for metrics.",
        example="--metric latency=1.2",
    )


__all__ = ["run_mlops_command"]
