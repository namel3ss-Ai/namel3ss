from __future__ import annotations

import os
from dataclasses import dataclass

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message


@dataclass(frozen=True)
class HeadlessApiOptions:
    api_token: str | None
    cors_origins: tuple[str, ...]


def extract_headless_api_flags(args: list[str]) -> tuple[list[str], HeadlessApiOptions]:
    remaining: list[str] = []
    api_token: str | None = None
    cors_origins: list[str] = []
    i = 0
    while i < len(args):
        token = args[i]
        if token == "--api-token":
            if i + 1 >= len(args):
                raise Namel3ssError(
                    build_guidance_message(
                        what="--api-token flag is missing a value.",
                        why="Headless API authentication requires a token string.",
                        fix="Provide a non-empty token value.",
                        example="n3 run app.ai --headless --api-token dev-secret",
                    )
                )
            value = str(args[i + 1] or "").strip()
            if not value:
                raise Namel3ssError(
                    build_guidance_message(
                        what="--api-token cannot be empty.",
                        why="Headless API authentication requires a token string.",
                        fix="Provide a non-empty token value.",
                        example="n3 run app.ai --headless --api-token dev-secret",
                    )
                )
            api_token = value
            i += 2
            continue
        if token == "--cors-origin":
            if i + 1 >= len(args):
                raise Namel3ssError(
                    build_guidance_message(
                        what="--cors-origin flag is missing a value.",
                        why="Headless API CORS requires an origin allow-list entry.",
                        fix="Provide one origin, or a comma-separated list.",
                        example="n3 run app.ai --headless --cors-origin https://frontend.example.com",
                    )
                )
            cors_origins.extend(_parse_origins(args[i + 1]))
            i += 2
            continue
        remaining.append(token)
        i += 1
    return remaining, HeadlessApiOptions(api_token=api_token, cors_origins=_dedupe(cors_origins))


def resolve_headless_api_token(explicit_value: str | None) -> str | None:
    if explicit_value is not None:
        value = explicit_value.strip()
        return value or None
    env_value = str(os.getenv("N3_HEADLESS_API_TOKEN") or "").strip()
    return env_value or None


def resolve_headless_cors_origins(explicit_values: tuple[str, ...]) -> tuple[str, ...]:
    if explicit_values:
        return explicit_values
    env_value = str(os.getenv("N3_HEADLESS_CORS_ORIGINS") or "").strip()
    if not env_value:
        return tuple()
    return _parse_origins(env_value)


def _parse_origins(raw: object) -> tuple[str, ...]:
    text = str(raw or "")
    items = [segment.strip() for segment in text.split(",")]
    values = [segment for segment in items if segment]
    return _dedupe(values)


def _dedupe(values: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return tuple(ordered)


__all__ = [
    "HeadlessApiOptions",
    "extract_headless_api_flags",
    "resolve_headless_api_token",
    "resolve_headless_cors_origins",
]
