from __future__ import annotations

from base64 import b64encode

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message


def normalize_tool_name(value: object) -> str:
    text = _optional_text(value) or "mlflow"
    allowed = {"mlflow", "dvc", "wandb"}
    if text not in allowed:
        raise Namel3ssError(
            build_guidance_message(
                what=f'Unsupported MLOps tool "{text}".',
                why="tool must be mlflow, dvc, or wandb.",
                fix="Set tool in mlops.yaml to one of the supported values.",
                example="tool: mlflow",
            )
        )
    return text


def normalize_auth_map(value: object) -> dict[str, str]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise Namel3ssError(_invalid_auth_message("auth must be a mapping"))
    auth: dict[str, str] = {}
    for key in sorted(value.keys()):
        raw = value.get(key)
        text = _optional_text(raw)
        if text is None:
            continue
        auth[str(key)] = text
    return auth


def normalize_training_backends(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise Namel3ssError(
            build_guidance_message(
                what="mlops.yaml is invalid.",
                why="training_backends must be a list.",
                fix="Set training_backends as a list of backend names.",
                example="training_backends:\n  - huggingface",
            )
        )
    values: list[str] = []
    seen: set[str] = set()
    for item in value:
        text = _optional_text(item)
        if not text or text in seen:
            continue
        seen.add(text)
        values.append(text)
    return tuple(sorted(values))


def auth_header_for_config(*, auth_token: str | None, auth: dict[str, str]) -> str | None:
    token = auth_token or auth.get("token") or auth.get("bearer_token")
    if token:
        return f"Bearer {token}"
    username = auth.get("username")
    password = auth.get("password")
    if username and password:
        raw = f"{username}:{password}".encode("utf-8")
        return f"Basic {b64encode(raw).decode('ascii')}"
    authorization = auth.get("authorization")
    if authorization:
        return authorization
    return None


def _optional_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text if text else None


def _invalid_auth_message(details: str) -> str:
    return build_guidance_message(
        what="mlops.yaml auth is invalid.",
        why=details,
        fix="Set auth as a mapping with token or username/password.",
        example="auth:\n  token: secret-token",
    )


__all__ = [
    "auth_header_for_config",
    "normalize_auth_map",
    "normalize_tool_name",
    "normalize_training_backends",
]
