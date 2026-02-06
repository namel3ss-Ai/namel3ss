from __future__ import annotations

from pathlib import Path

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.server.prod.security_requirements import build_tls_context_if_required


def _write_app(tmp_path: Path) -> Path:
    app = tmp_path / "app.ai"
    app.write_text('spec is "1.0"\n\nflow "demo":\n  return "ok"\n', encoding="utf-8")
    return app


def test_production_tls_not_required_outside_production_mode(tmp_path: Path, monkeypatch) -> None:
    app = _write_app(tmp_path)
    monkeypatch.delenv("N3_ENV", raising=False)
    assert build_tls_context_if_required(project_root=tmp_path, app_path=app) is None


def test_production_mode_requires_auth_and_security_config(tmp_path: Path, monkeypatch) -> None:
    app = _write_app(tmp_path)
    monkeypatch.setenv("N3_ENV", "production")
    monkeypatch.delenv("N3_TLS_CERT_PATH", raising=False)
    monkeypatch.delenv("N3_TLS_KEY_PATH", raising=False)
    with pytest.raises(Namel3ssError) as exc:
        build_tls_context_if_required(project_root=tmp_path, app_path=app)
    assert "auth.yaml" in exc.value.message


def test_production_mode_requires_tls_paths(tmp_path: Path, monkeypatch) -> None:
    app = _write_app(tmp_path)
    (tmp_path / "auth.yaml").write_text(
        (
            'version: "1.0"\n'
            "roles:\n"
            "  admin:\n"
            "    permissions:\n"
            "      - records.update\n"
            "authentication:\n"
            "  methods:\n"
            "    password: true\n"
            "    bearer_token: true\n"
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
    monkeypatch.setenv("N3_ENV", "production")
    monkeypatch.delenv("N3_TLS_CERT_PATH", raising=False)
    monkeypatch.delenv("N3_TLS_KEY_PATH", raising=False)
    with pytest.raises(Namel3ssError) as exc:
        build_tls_context_if_required(project_root=tmp_path, app_path=app)
    assert "N3_TLS_CERT_PATH" in exc.value.message
