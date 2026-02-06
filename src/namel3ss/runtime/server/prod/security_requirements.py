from __future__ import annotations

import os
import ssl
from pathlib import Path

from namel3ss.config.security_compliance import load_auth_config, load_security_config
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message


def build_tls_context_if_required(
    *,
    project_root: Path,
    app_path: Path,
) -> ssl.SSLContext | None:
    if not _production_mode_enabled():
        return None
    # In production mode, security config must exist and be valid before serving traffic.
    load_auth_config(project_root, app_path, required=True)
    load_security_config(project_root, app_path, required=True)

    cert_path = _required_env_path("N3_TLS_CERT_PATH")
    key_path = _required_env_path("N3_TLS_KEY_PATH")
    if not cert_path.exists():
        raise Namel3ssError(_missing_tls_file_message("N3_TLS_CERT_PATH", cert_path))
    if not key_path.exists():
        raise Namel3ssError(_missing_tls_file_message("N3_TLS_KEY_PATH", key_path))

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    if hasattr(ssl, "TLSVersion"):
        context.minimum_version = ssl.TLSVersion.TLSv1_2
    try:
        context.load_cert_chain(certfile=cert_path.as_posix(), keyfile=key_path.as_posix())
    except Exception as err:
        raise Namel3ssError(_invalid_tls_chain_message(cert_path, key_path, str(err))) from err
    return context


def _production_mode_enabled() -> bool:
    return os.getenv("N3_ENV", "").strip().lower() == "production"


def _required_env_path(env_name: str) -> Path:
    value = os.getenv(env_name, "").strip()
    if value:
        return Path(value).expanduser().resolve()
    raise Namel3ssError(_missing_tls_env_message(env_name))


def _missing_tls_env_message(env_name: str) -> str:
    return build_guidance_message(
        what=f"{env_name} is required in production mode.",
        why="Production runner refuses insecure HTTP startup.",
        fix="Set TLS certificate and key paths before starting the server.",
        example="N3_ENV=production N3_TLS_CERT_PATH=./cert.pem N3_TLS_KEY_PATH=./key.pem n3 start",
    )


def _missing_tls_file_message(env_name: str, path: Path) -> str:
    return build_guidance_message(
        what=f"{env_name} points to a missing file.",
        why=f"TLS startup could not find {path.as_posix()}.",
        fix="Point the environment variable to an existing certificate/key file.",
        example=f"{env_name}={path.as_posix()}",
    )


def _invalid_tls_chain_message(cert_path: Path, key_path: Path, reason: str) -> str:
    return build_guidance_message(
        what="TLS certificate or key could not be loaded.",
        why=f"Failed to load cert '{cert_path.as_posix()}' and key '{key_path.as_posix()}': {reason}.",
        fix="Use a valid certificate/key pair and retry.",
        example="openssl req -x509 -newkey rsa:2048 -nodes -keyout key.pem -out cert.pem -days 1",
    )


__all__ = ["build_tls_context_if_required"]
