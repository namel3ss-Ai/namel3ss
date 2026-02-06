from __future__ import annotations

from pathlib import Path

import pytest

from namel3ss.config.security_compliance import (
    load_auth_config,
    load_retention_config,
    load_security_config,
)
from namel3ss.errors.base import Namel3ssError


def _write_app(tmp_path: Path) -> Path:
    app_path = tmp_path / "app.ai"
    app_path.write_text('spec is "1.0"\n\nflow "demo":\n  return "ok"\n', encoding="utf-8")
    return app_path


def test_load_security_compliance_configs(tmp_path: Path) -> None:
    app_path = _write_app(tmp_path)
    (tmp_path / "auth.yaml").write_text(
        (
            'version: "1.0"\n'
            "roles:\n"
            "  admin:\n"
            "    permissions:\n"
            "      - records.delete\n"
            "authentication:\n"
            "  methods:\n"
            "    password: true\n"
            "    bearer_token: false\n"
        ),
        encoding="utf-8",
    )
    (tmp_path / "security.yaml").write_text(
        (
            'version: "1.0"\n'
            "encryption:\n"
            "  enabled: true\n"
            '  algorithm: "aes-256-gcm"\n'
            "  key: env:N3_ENCRYPTION_KEY\n"
            "resource_limits:\n"
            "  max_memory_mb: 256\n"
            "  max_cpu_ms: 5000\n"
        ),
        encoding="utf-8",
    )
    (tmp_path / "retention.yaml").write_text(
        (
            'version: "1.0"\n'
            "records:\n"
            "  orders:\n"
            "    retention_days: 30\n"
            "    anonymize_fields:\n"
            "      - customer_email\n"
            "audit:\n"
            "  enabled: true\n"
            "  retention_days: 90\n"
        ),
        encoding="utf-8",
    )

    auth = load_auth_config(tmp_path, app_path, required=True)
    security = load_security_config(tmp_path, app_path, required=True)
    retention = load_retention_config(tmp_path, app_path, required=True)

    assert auth is not None
    assert security is not None
    assert retention is not None
    assert auth.methods["password"] is True
    assert auth.methods["bearer_token"] is False
    assert security.encryption_key_ref == "env:N3_ENCRYPTION_KEY"
    assert retention.records["orders"].retention_days == 30


def test_security_config_requires_env_key_reference(tmp_path: Path) -> None:
    app_path = _write_app(tmp_path)
    (tmp_path / "security.yaml").write_text(
        (
            'version: "1.0"\n'
            "encryption:\n"
            "  enabled: true\n"
            '  algorithm: "aes-256-gcm"\n'
            '  key: "plain-text-key"\n'
            "resource_limits:\n"
            "  max_memory_mb: 128\n"
            "  max_cpu_ms: 1000\n"
        ),
        encoding="utf-8",
    )
    with pytest.raises(Namel3ssError) as exc:
        load_security_config(tmp_path, app_path, required=True)
    assert "env reference" in exc.value.message.lower()


def test_unknown_security_yaml_keys_are_rejected(tmp_path: Path) -> None:
    app_path = _write_app(tmp_path)
    (tmp_path / "security.yaml").write_text(
        'version: "1.0"\nunknown_field: true\n',
        encoding="utf-8",
    )
    with pytest.raises(Namel3ssError) as exc:
        load_security_config(tmp_path, app_path, required=True)
    assert "unknown key" in exc.value.message.lower()
