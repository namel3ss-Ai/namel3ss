from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.persistence_paths import resolve_project_root
from namel3ss.utils.simple_yaml import parse_yaml, render_yaml


OBSERVABILITY_FILENAME = "observability.yaml"
DEFAULT_BATCH_SIZE = 64
DEFAULT_MAX_TRACE_SIZE = 2000


@dataclass(frozen=True)
class OTLPConfig:
    endpoint: str
    auth: dict[str, object]
    batch_size: int

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "endpoint": self.endpoint,
            "batch_size": int(self.batch_size),
        }
        if self.auth:
            payload["auth"] = dict(self.auth)
        else:
            payload["auth"] = {}
        return payload


@dataclass(frozen=True)
class ObservabilityConfig:
    redaction_rules: dict[str, str]
    otlp_config: OTLPConfig
    metrics_enabled: bool
    max_trace_size: int

    def to_dict(self) -> dict[str, object]:
        return {
            "redaction_rules": dict(sorted(self.redaction_rules.items())),
            "otlp_config": self.otlp_config.to_dict(),
            "metrics_enabled": bool(self.metrics_enabled),
            "max_trace_size": int(self.max_trace_size),
        }


def observability_config_path(project_root: str | Path | None, app_path: str | Path | None) -> Path | None:
    root = resolve_project_root(project_root, app_path)
    if root is None:
        return None
    return Path(root) / OBSERVABILITY_FILENAME


def load_observability_config(project_root: str | Path | None, app_path: str | Path | None) -> ObservabilityConfig:
    path = observability_config_path(project_root, app_path)
    if path is None or not path.exists():
        return default_observability_config()
    try:
        payload = parse_yaml(path.read_text(encoding="utf-8"))
    except Exception as err:
        raise Namel3ssError(_invalid_config_message(path, str(err))) from err
    if not isinstance(payload, dict):
        raise Namel3ssError(_invalid_config_message(path, "expected a YAML mapping"))
    return _parse_config_payload(payload, path=path)


def init_observability_config(
    project_root: str | Path | None,
    app_path: str | Path | None,
    *,
    overwrite: bool = False,
) -> Path:
    path = observability_config_path(project_root, app_path)
    if path is None:
        raise Namel3ssError(
            build_guidance_message(
                what="Observability config path could not be resolved.",
                why="The project root is missing.",
                fix="Run this command from a project with app.ai.",
                example="n3 observability init app.ai",
            )
        )
    if path.exists() and not overwrite:
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    config = default_observability_config()
    path.write_text(render_yaml(config.to_dict()), encoding="utf-8")
    return path


def default_observability_config() -> ObservabilityConfig:
    return ObservabilityConfig(
        redaction_rules={},
        otlp_config=OTLPConfig(endpoint="", auth={}, batch_size=DEFAULT_BATCH_SIZE),
        metrics_enabled=True,
        max_trace_size=DEFAULT_MAX_TRACE_SIZE,
    )


def _parse_config_payload(payload: dict[str, object], *, path: Path) -> ObservabilityConfig:
    redaction_raw = payload.get("redaction_rules", {})
    if isinstance(redaction_raw, str) and redaction_raw.strip() in {"", "{}", "null"}:
        redaction_raw = {}
    redaction_rules: dict[str, str] = {}
    if isinstance(redaction_raw, dict):
        for raw_key in sorted(redaction_raw.keys(), key=lambda item: str(item)):
            key = str(raw_key).strip()
            if not key:
                continue
            value = redaction_raw.get(raw_key)
            replacement = str(value).strip() if value is not None else "[REDACTED]"
            redaction_rules[key] = replacement or "[REDACTED]"
    elif redaction_raw is not None:
        raise Namel3ssError(_invalid_config_message(path, "redaction_rules must be a mapping"))

    otlp_raw = payload.get("otlp_config", {})
    if otlp_raw is None:
        otlp_raw = {}
    if not isinstance(otlp_raw, dict):
        raise Namel3ssError(_invalid_config_message(path, "otlp_config must be a mapping"))

    endpoint = str(otlp_raw.get("endpoint", payload.get("otlp_endpoint", "")) or "").strip()
    auth_raw = otlp_raw.get("auth", {})
    if auth_raw is None:
        auth_raw = {}
    if isinstance(auth_raw, str) and auth_raw.strip() in {"", "{}", "null"}:
        auth_raw = {}
    if not isinstance(auth_raw, dict):
        raise Namel3ssError(_invalid_config_message(path, "otlp_config.auth must be a mapping"))
    auth = {str(key): auth_raw[key] for key in sorted(auth_raw.keys(), key=lambda item: str(item))}
    batch_size = _parse_positive_int(
        otlp_raw.get("batch_size", DEFAULT_BATCH_SIZE),
        field="otlp_config.batch_size",
        path=path,
    )
    metrics_enabled = _parse_bool(payload.get("metrics_enabled", True), field="metrics_enabled", path=path)
    max_trace_size = _parse_positive_int(
        payload.get("max_trace_size", DEFAULT_MAX_TRACE_SIZE),
        field="max_trace_size",
        path=path,
    )
    return ObservabilityConfig(
        redaction_rules=redaction_rules,
        otlp_config=OTLPConfig(endpoint=endpoint, auth=auth, batch_size=batch_size),
        metrics_enabled=metrics_enabled,
        max_trace_size=max_trace_size,
    )


def _parse_bool(value: object, *, field: str, path: Path) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "yes", "1"}:
            return True
        if lowered in {"false", "no", "0"}:
            return False
    raise Namel3ssError(_invalid_config_message(path, f"{field} must be true or false"))


def _parse_positive_int(value: object, *, field: str, path: Path) -> int:
    if isinstance(value, bool):
        raise Namel3ssError(_invalid_config_message(path, f"{field} must be a positive integer"))
    try:
        parsed = int(value)
    except Exception as err:
        raise Namel3ssError(_invalid_config_message(path, f"{field} must be a positive integer")) from err
    if parsed <= 0:
        raise Namel3ssError(_invalid_config_message(path, f"{field} must be greater than 0"))
    return parsed


def _invalid_config_message(path: Path, details: str) -> str:
    return build_guidance_message(
        what="observability.yaml is invalid.",
        why=f"{path.as_posix()} could not be parsed: {details}.",
        fix="Use deterministic YAML fields: redaction_rules, otlp_config, metrics_enabled, max_trace_size.",
        example=(
            "redaction_rules:\n"
            "  input.password: \"[REDACTED]\"\n"
            "otlp_config:\n"
            "  endpoint: \"\"\n"
            "  auth: {}\n"
            "  batch_size: 64\n"
            "metrics_enabled: true\n"
            "max_trace_size: 2000"
        ),
    )


__all__ = [
    "DEFAULT_BATCH_SIZE",
    "DEFAULT_MAX_TRACE_SIZE",
    "OBSERVABILITY_FILENAME",
    "OTLPConfig",
    "ObservabilityConfig",
    "default_observability_config",
    "init_observability_config",
    "load_observability_config",
    "observability_config_path",
]
