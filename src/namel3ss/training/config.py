from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.utils.simple_yaml import parse_yaml

DEFAULT_EPOCHS = 1
DEFAULT_LEARNING_RATE = 2e-5
DEFAULT_SEED = 13
DEFAULT_MODALITY = "text"
DEFAULT_VALIDATION_SPLIT = 0.2
SUPPORTED_MODALITIES = ("text", "image", "audio")
SUPPORTED_MODEL_BASES: dict[str, tuple[str, ...]] = {
    "text": (
        "gpt-3.5-turbo",
        "gpt-4",
        "text-base",
    ),
    "image": (
        "vision-classifier",
        "vision-generator",
        "vision-model-id",
    ),
    "audio": (
        "speech-to-text",
        "speech-synth",
        "speech-model-id",
    ),
}


@dataclass(frozen=True)
class TrainingConfig:
    project_root: Path
    app_path: Path
    model_base: str
    dataset_path: Path
    output_name: str
    epochs: int
    learning_rate: float
    seed: int
    modality: str
    validation_split: float
    output_dir: Path
    report_dir: Path


def load_training_config_file(path: Path) -> dict[str, object]:
    if not path.exists():
        raise Namel3ssError(
            build_guidance_message(
                what=f"Training config file not found: {path}",
                why="The --config path must point to an existing YAML file.",
                fix="Create the file or pass the correct path.",
                example="n3 train --config training.yaml",
            )
        )
    try:
        payload = parse_yaml(path.read_text(encoding="utf-8"))
    except Exception as err:
        raise Namel3ssError(
            build_guidance_message(
                what="Training config could not be parsed.",
                why=str(err),
                fix="Use valid YAML with key:value entries.",
                example=(
                    "model_base: gpt-3.5-turbo\n"
                    "dataset: data/train.jsonl\n"
                    "output_name: supportbot.faq_model_v2"
                ),
            )
        ) from err
    if not isinstance(payload, dict):
        raise Namel3ssError(
            build_guidance_message(
                what="Training config must be a mapping.",
                why="The root YAML value was not a key/value object.",
                fix="Use top-level keys for training options.",
                example="model_base: gpt-3.5-turbo",
            )
        )
    return {str(key): payload[key] for key in payload.keys()}


def resolve_training_config(
    *,
    project_root: Path,
    app_path: Path,
    config_values: dict[str, object] | None,
    overrides: dict[str, object],
) -> TrainingConfig:
    values = dict(config_values or {})
    for key, value in overrides.items():
        if value is not None:
            values[key] = value

    model_base = _required_text(values.get("model_base"), field="model_base")
    output_name = _required_text(values.get("output_name"), field="output_name")

    dataset_raw = values.get("dataset")
    dataset_path = _resolve_dataset_path(dataset_raw, project_root=project_root)

    epochs = _coerce_int(values.get("epochs", DEFAULT_EPOCHS), field="epochs", minimum=1)
    learning_rate = _coerce_float(
        values.get("learning_rate", DEFAULT_LEARNING_RATE),
        field="learning_rate",
        minimum=0.0,
        allow_zero=False,
    )
    seed = _coerce_int(values.get("seed", DEFAULT_SEED), field="seed", minimum=0)
    modality = _normalize_modality(values.get("mode") or values.get("modality") or DEFAULT_MODALITY)
    validation_split = _coerce_float(
        values.get("validation_split", DEFAULT_VALIDATION_SPLIT),
        field="validation_split",
        minimum=0.0,
        allow_zero=False,
    )
    if validation_split >= 1.0:
        raise Namel3ssError(_invalid_value_message("validation_split", str(validation_split), "must be less than 1.0"))

    output_dir = _resolve_optional_path(
        values.get("output_dir"),
        project_root=project_root,
        default="models",
        field_name="output_dir",
    )
    report_dir = _resolve_optional_path(
        values.get("report_dir"),
        project_root=project_root,
        default="docs/reports",
        field_name="report_dir",
    )

    _validate_model_support(model_base=model_base, modality=modality)

    return TrainingConfig(
        project_root=project_root,
        app_path=app_path,
        model_base=model_base,
        dataset_path=dataset_path,
        output_name=output_name,
        epochs=epochs,
        learning_rate=learning_rate,
        seed=seed,
        modality=modality,
        validation_split=validation_split,
        output_dir=output_dir,
        report_dir=report_dir,
    )


def _resolve_dataset_path(value: object, *, project_root: Path) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise Namel3ssError(
            build_guidance_message(
                what="dataset is required.",
                why="Training needs a JSONL dataset path.",
                fix="Provide --dataset or set dataset in --config.",
                example="n3 train --model-base gpt-3.5-turbo --dataset data/train.jsonl --output-name supportbot.faq_model_v2",
            )
        )
    raw = value.strip()
    path = Path(raw)
    if not path.is_absolute():
        path = (project_root / path).resolve()
    else:
        path = path.resolve()
    if not path.exists() or not path.is_file():
        raise Namel3ssError(
            build_guidance_message(
                what=f"dataset file not found: {raw}",
                why="The training dataset path does not exist.",
                fix="Create the file or pass a valid JSONL path.",
                example="--dataset data/support_tickets.jsonl",
            )
        )
    return path


def _resolve_optional_path(value: object, *, project_root: Path, default: str, field_name: str) -> Path:
    if value is None:
        return (project_root / default).resolve()
    if not isinstance(value, str) or not value.strip():
        raise Namel3ssError(_invalid_value_message(field_name, str(value), "must be a path string"))
    path = Path(value.strip())
    if not path.is_absolute():
        path = (project_root / path).resolve()
    else:
        path = path.resolve()
    return path


def _required_text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise Namel3ssError(
            build_guidance_message(
                what=f"{field} is required.",
                why=f"Training cannot start without {field}.",
                fix=f"Pass --{field.replace('_', '-')} or set {field} in config.",
                example=f"{field}: value",
            )
        )
    return value.strip()


def _coerce_int(value: object, *, field: str, minimum: int) -> int:
    if isinstance(value, bool):
        raise Namel3ssError(_invalid_value_message(field, str(value), "must be an integer"))
    try:
        parsed = int(value)
    except Exception as err:
        raise Namel3ssError(_invalid_value_message(field, str(value), "must be an integer")) from err
    if parsed < minimum:
        raise Namel3ssError(_invalid_value_message(field, str(value), f"must be >= {minimum}"))
    return parsed


def _coerce_float(value: object, *, field: str, minimum: float, allow_zero: bool) -> float:
    if isinstance(value, bool):
        raise Namel3ssError(_invalid_value_message(field, str(value), "must be a number"))
    try:
        parsed = float(value)
    except Exception as err:
        raise Namel3ssError(_invalid_value_message(field, str(value), "must be a number")) from err
    if parsed < minimum or (not allow_zero and parsed == 0.0):
        op = ">=" if allow_zero else ">"
        raise Namel3ssError(_invalid_value_message(field, str(value), f"must be {op} {minimum}"))
    return parsed


def _normalize_modality(value: object) -> str:
    if not isinstance(value, str):
        raise Namel3ssError(_invalid_value_message("mode", str(value), "must be text, image, or audio"))
    token = value.strip().lower()
    if token not in SUPPORTED_MODALITIES:
        choices = ", ".join(SUPPORTED_MODALITIES)
        raise Namel3ssError(_invalid_value_message("mode", token, f"must be one of: {choices}"))
    return token


def _validate_model_support(*, model_base: str, modality: str) -> None:
    supported = SUPPORTED_MODEL_BASES.get(modality, ())
    if model_base in supported:
        return
    suggestion = supported[0] if supported else "gpt-3.5-turbo"
    raise Namel3ssError(
        build_guidance_message(
            what=f"Model base '{model_base}' does not support mode '{modality}'.",
            why="The selected modality requires a compatible approved base model.",
            fix="Choose a supported model base for this modality.",
            example=f"--mode {modality} --model-base {suggestion}",
        )
    )


def _invalid_value_message(field: str, value: str, details: str) -> str:
    return build_guidance_message(
        what=f"Invalid value for {field}: {value}",
        why=f"{field} {details}.",
        fix="Correct the value and retry.",
        example=f"n3 train --{field.replace('_', '-')} <value>",
    )


__all__ = [
    "DEFAULT_EPOCHS",
    "DEFAULT_LEARNING_RATE",
    "DEFAULT_MODALITY",
    "DEFAULT_SEED",
    "DEFAULT_VALIDATION_SPLIT",
    "SUPPORTED_MODALITIES",
    "SUPPORTED_MODEL_BASES",
    "TrainingConfig",
    "load_training_config_file",
    "resolve_training_config",
]
