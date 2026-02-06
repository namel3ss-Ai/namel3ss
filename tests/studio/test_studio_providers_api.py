from __future__ import annotations

import json
from pathlib import Path

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.studio.providers_api import apply_providers_payload, get_providers_payload


SOURCE = '''spec is "1.0"

capabilities:
  huggingface

ai "assistant":
  model is "huggingface:bert-base-uncased"

flow "demo":
  ask ai "assistant" with input: "hello" as reply
  return reply

page "home":
  button "Run":
    calls flow "demo"
'''


def _write_app(tmp_path: Path) -> Path:
    app_path = tmp_path / "app.ai"
    app_path.write_text(SOURCE, encoding="utf-8")
    return app_path


def test_get_providers_payload_includes_provider_rows(tmp_path: Path) -> None:
    app_path = _write_app(tmp_path)
    payload = get_providers_payload(SOURCE, app_path.as_posix())
    assert payload["ok"] is True
    providers = payload["providers"]
    names = [row["name"] for row in providers]
    assert names == sorted(names)
    assert "huggingface" in names
    huggingface = next(row for row in providers if row["name"] == "huggingface")
    assert huggingface["used_in_app"] is True
    assert "huggingface:bert-base-uncased" in huggingface["models"]


def test_apply_providers_payload_persists_settings(tmp_path: Path) -> None:
    app_path = _write_app(tmp_path)
    body = {
        "action": "save",
        "settings": {
            "huggingface": {
                "default_model": "huggingface:facebook/bart-large-cnn",
                "secret_name": "NAMEL3SS_HUGGINGFACE_API_KEY",
            },
            "vision_gen": {
                "default_model": "vision_gen:stable-diffusion",
                "secret_name": "",
            },
        },
    }
    payload = apply_providers_payload(SOURCE, body, app_path.as_posix())
    assert payload["ok"] is True
    settings_path = tmp_path / ".namel3ss" / "provider_settings.json"
    assert settings_path.exists()
    saved = json.loads(settings_path.read_text(encoding="utf-8"))
    assert saved["schema_version"] == 1
    assert saved["providers"]["huggingface"]["default_model"] == "huggingface:facebook/bart-large-cnn"
    assert saved["providers"]["huggingface"]["secret_name"] == "NAMEL3SS_HUGGINGFACE_API_KEY"
    assert saved["providers"]["vision_gen"]["default_model"] == "vision_gen:stable-diffusion"


def test_apply_providers_payload_rejects_invalid_model(tmp_path: Path) -> None:
    app_path = _write_app(tmp_path)
    with pytest.raises(Namel3ssError) as err:
        apply_providers_payload(
            SOURCE,
            {
                "action": "save",
                "settings": {
                    "huggingface": {
                        "default_model": "vision_gen:stable-diffusion",
                    }
                },
            },
            app_path.as_posix(),
        )
    assert "requires namespaced model identifiers" in str(err.value) or "Unknown model" in str(err.value)
