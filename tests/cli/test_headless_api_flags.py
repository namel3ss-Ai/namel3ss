from __future__ import annotations

import pytest

from namel3ss.cli.headless_api_flags import (
    extract_headless_api_flags,
    resolve_headless_api_token,
    resolve_headless_cors_origins,
)
from namel3ss.errors.base import Namel3ssError


def test_extract_headless_api_flags_parses_token_and_cors() -> None:
    remaining, options = extract_headless_api_flags(
        [
            "app.ai",
            "--api-token",
            "secret",
            "--cors-origin",
            "https://a.example.com,https://b.example.com",
            "--dry",
        ]
    )
    assert remaining == ["app.ai", "--dry"]
    assert options.api_token == "secret"
    assert options.cors_origins == ("https://a.example.com", "https://b.example.com")


def test_extract_headless_api_flags_rejects_empty_token() -> None:
    with pytest.raises(Namel3ssError):
        extract_headless_api_flags(["--api-token", ""])


def test_resolve_headless_api_values_fall_back_to_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("N3_HEADLESS_API_TOKEN", "env-token")
    monkeypatch.setenv("N3_HEADLESS_CORS_ORIGINS", "https://env.example.com,https://env2.example.com")
    assert resolve_headless_api_token(None) == "env-token"
    assert resolve_headless_cors_origins(tuple()) == ("https://env.example.com", "https://env2.example.com")
