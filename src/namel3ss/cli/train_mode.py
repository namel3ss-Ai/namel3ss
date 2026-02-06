from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys

from namel3ss.cli.app_path import resolve_app_path
from namel3ss.cli.text_output import prepare_cli_text
from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.errors.render import format_error
from namel3ss.runtime.capabilities.feature_gate import require_app_capability
from namel3ss.training import load_training_config_file, resolve_training_config, run_training_job


@dataclass(frozen=True)
class _TrainParams:
    app_arg: str | None
    json_mode: bool
    show_help: bool
    model_base: str | None = None
    dataset: str | None = None
    epochs: int | None = None
    learning_rate: float | None = None
    seed: int | None = None
    output_name: str | None = None
    mode: str | None = None
    validation_split: float | None = None
    config_path: str | None = None
    output_dir: str | None = None
    report_dir: str | None = None


def run_train_command(args: list[str]) -> int:
    try:
        params = _parse_args(args)
        if params.show_help:
            _print_usage()
            return 0

        app_path = resolve_app_path(params.app_arg)
        require_app_capability(app_path, "training")
        project_root = app_path.parent.resolve()

        config_values = None
        if params.config_path:
            config_path = Path(params.config_path)
            if not config_path.is_absolute():
                config_path = (Path.cwd() / config_path).resolve()
            else:
                config_path = config_path.resolve()
            config_values = load_training_config_file(config_path)

        config = resolve_training_config(
            project_root=project_root,
            app_path=app_path.resolve(),
            config_values=config_values,
            overrides={
                "model_base": params.model_base,
                "dataset": params.dataset,
                "epochs": params.epochs,
                "learning_rate": params.learning_rate,
                "seed": params.seed,
                "output_name": params.output_name,
                "mode": params.mode,
                "validation_split": params.validation_split,
                "output_dir": params.output_dir,
                "report_dir": params.report_dir,
            },
        )

        result = run_training_job(config)
        payload = result.to_dict()

        if params.json_mode:
            print(canonical_json_dumps(payload, pretty=True, drop_run_keys=False))
        else:
            _print_human_summary(payload)
        return 0
    except Namel3ssError as err:
        print(prepare_cli_text(format_error(err, None)), file=sys.stderr)
        return 1


def _parse_args(args: list[str]) -> _TrainParams:
    if not args:
        return _TrainParams(app_arg=None, json_mode=False, show_help=False)
    if args[0] in {"--help", "-h", "help"}:
        return _TrainParams(app_arg=None, json_mode=False, show_help=True)

    json_mode = False
    model_base = None
    dataset = None
    epochs = None
    learning_rate = None
    seed = None
    output_name = None
    mode = None
    validation_split = None
    config_path = None
    output_dir = None
    report_dir = None
    positional: list[str] = []

    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--json":
            json_mode = True
            i += 1
            continue
        if arg in {
            "--model-base",
            "--dataset",
            "--epochs",
            "--learning-rate",
            "--seed",
            "--output-name",
            "--mode",
            "--validation-split",
            "--config",
            "--output-dir",
            "--report-dir",
        }:
            if i + 1 >= len(args):
                raise Namel3ssError(_missing_option_value_message(arg))
            value = args[i + 1]
            if arg == "--model-base":
                model_base = value
            elif arg == "--dataset":
                dataset = value
            elif arg == "--epochs":
                epochs = _parse_int(arg, value)
            elif arg == "--learning-rate":
                learning_rate = _parse_float(arg, value)
            elif arg == "--seed":
                seed = _parse_int(arg, value)
            elif arg == "--output-name":
                output_name = value
            elif arg == "--mode":
                mode = value
            elif arg == "--validation-split":
                validation_split = _parse_float(arg, value)
            elif arg == "--config":
                config_path = value
            elif arg == "--output-dir":
                output_dir = value
            elif arg == "--report-dir":
                report_dir = value
            i += 2
            continue
        if arg.startswith("--"):
            raise Namel3ssError(_unknown_flag_message(arg))
        positional.append(arg)
        i += 1

    app_arg = positional[0] if positional else None
    if len(positional) > 1:
        raise Namel3ssError(_too_many_positional_args_message())

    return _TrainParams(
        app_arg=app_arg,
        json_mode=json_mode,
        show_help=False,
        model_base=model_base,
        dataset=dataset,
        epochs=epochs,
        learning_rate=learning_rate,
        seed=seed,
        output_name=output_name,
        mode=mode,
        validation_split=validation_split,
        config_path=config_path,
        output_dir=output_dir,
        report_dir=report_dir,
    )


def _parse_int(flag: str, value: str) -> int:
    try:
        parsed = int(value)
    except Exception as err:
        raise Namel3ssError(_invalid_number_message(flag, value)) from err
    return parsed


def _parse_float(flag: str, value: str) -> float:
    try:
        parsed = float(value)
    except Exception as err:
        raise Namel3ssError(_invalid_number_message(flag, value)) from err
    return parsed


def _print_usage() -> None:
    print(
        "Usage:\n"
        "  n3 train --model-base MODEL --dataset DATASET.jsonl --output-name NAME [app.ai] [--epochs N] [--learning-rate LR] [--seed N] [--mode text|image|audio] [--validation-split RATIO] [--output-dir DIR] [--report-dir DIR] [--json]\n"
        "  n3 train --config training.yaml [app.ai] [--json]"
    )


def _print_human_summary(payload: dict[str, object]) -> None:
    print("Training")
    print(f"  ok: {payload.get('ok')}")
    print(f"  model: {payload.get('model_ref')}")
    print(f"  artifact_path: {payload.get('artifact_path')}")
    print(f"  report_path: {payload.get('report_path')}")
    metrics = payload.get("metrics")
    if isinstance(metrics, dict):
        print("  metrics:")
        for key in sorted(metrics.keys()):
            print(f"    {key}: {metrics[key]}")


def _unknown_flag_message(flag: str) -> str:
    return build_guidance_message(
        what=f"Unknown flag '{flag}'.",
        why="n3 train only accepts documented training flags.",
        fix="Remove the unsupported flag.",
        example="n3 train --model-base gpt-3.5-turbo --dataset data/train.jsonl --output-name mymodel.v1",
    )


def _missing_option_value_message(flag: str) -> str:
    return build_guidance_message(
        what=f"Flag '{flag}' is missing a value.",
        why="This option requires a value.",
        fix="Provide a value after the flag.",
        example=f"{flag} value",
    )


def _invalid_number_message(flag: str, value: str) -> str:
    return build_guidance_message(
        what=f"Flag '{flag}' received invalid numeric value '{value}'.",
        why="This option expects a numeric value.",
        fix="Use a valid integer or float.",
        example="--epochs 3",
    )


def _too_many_positional_args_message() -> str:
    return build_guidance_message(
        what="Too many positional arguments for n3 train.",
        why="Only one optional app path is supported.",
        fix="Pass at most one app path argument.",
        example="n3 train --model-base gpt-3.5-turbo --dataset data/train.jsonl --output-name supportbot.faq_model_v2 app.ai",
    )


__all__ = ["run_train_command"]
