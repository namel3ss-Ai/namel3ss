from __future__ import annotations

from pathlib import Path

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.security_encryption import EncryptionService, initialize_encryption_key, load_encryption_service


def _write_security_yaml(tmp_path: Path, *, algorithm: str, enabled: bool = True) -> None:
    (tmp_path / "security.yaml").write_text(
        (
            'version: "1.0"\n'
            "encryption:\n"
            f"  enabled: {str(enabled).lower()}\n"
            f'  algorithm: "{algorithm}"\n'
            "  key: env:N3_ENCRYPTION_KEY\n"
            "resource_limits:\n"
            "  max_memory_mb: 64\n"
            "  max_cpu_ms: 5000\n"
        ),
        encoding="utf-8",
    )


def test_load_encryption_service_reads_algorithm_from_security_config(tmp_path: Path, monkeypatch) -> None:
    app_path = tmp_path / "app.ai"
    app_path.write_text('spec is "1.0"\nflow "demo":\n  return "ok"\n', encoding="utf-8")
    _write_security_yaml(tmp_path, algorithm="aes-256-gcm")
    fake_home = tmp_path / ".home"
    monkeypatch.setattr(Path, "home", lambda: fake_home)
    initialize_encryption_key(tmp_path, app_path)

    service = load_encryption_service(tmp_path, app_path, required=True)
    assert service is not None
    assert service.algorithm == "aes-256-gcm"
    token = service.encrypt_text("secret")
    assert service.decrypt_text(token) == "secret"


def test_load_encryption_service_rejects_unsupported_algorithm(tmp_path: Path, monkeypatch) -> None:
    app_path = tmp_path / "app.ai"
    app_path.write_text('spec is "1.0"\nflow "demo":\n  return "ok"\n', encoding="utf-8")
    _write_security_yaml(tmp_path, algorithm="chacha20")
    fake_home = tmp_path / ".home"
    monkeypatch.setattr(Path, "home", lambda: fake_home)
    initialize_encryption_key(tmp_path, app_path)

    with pytest.raises(Namel3ssError) as exc:
        load_encryption_service(tmp_path, app_path, required=True)
    assert "not supported" in exc.value.message


def test_decrypt_rejects_algorithm_mismatch() -> None:
    service_gcm = EncryptionService(key=b"k" * 32, algorithm="aes-256-gcm")
    token = service_gcm.encrypt_text("value")
    service_ctr = EncryptionService(key=b"k" * 32, algorithm="aes-256-ctr")
    with pytest.raises(Namel3ssError) as exc:
        service_ctr.decrypt_text(token)
    assert "does not match" in exc.value.message

