from __future__ import annotations

import base64
import hashlib
import os
from dataclasses import dataclass
from pathlib import Path

from namel3ss.config.security_compliance import load_security_config
from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.persistence_paths import resolve_project_root
from namel3ss.utils.slugify import slugify_text
from namel3ss.crypto.aes import AESCipher


ENCRYPTION_PREFIX = "enc:v1:"
ENCRYPTED_MARKER = "__n3_encrypted__"
DEFAULT_ENCRYPTION_ALGORITHM = "aes-256-ctr"
SUPPORTED_ENCRYPTION_ALGORITHMS = ("aes-256-ctr", "aes-256-gcm")


@dataclass(frozen=True)
class EncryptionService:
    key: bytes
    algorithm: str = DEFAULT_ENCRYPTION_ALGORITHM

    def encrypt_text(self, text: str) -> str:
        payload = text.encode("utf-8")
        token = _encrypt_bytes(self.key, payload, self.algorithm)
        return token

    def decrypt_text(self, token: str) -> str:
        raw = _decrypt_bytes(self.key, token, expected_algorithm=self.algorithm)
        return raw.decode("utf-8")

    def encrypt_json(self, value: object) -> str:
        payload = canonical_json_dumps(value, pretty=False, drop_run_keys=False).encode("utf-8")
        return _encrypt_bytes(self.key, payload, self.algorithm)

    def decrypt_json(self, token: str) -> object:
        raw = _decrypt_bytes(self.key, token, expected_algorithm=self.algorithm)
        try:
            import json

            return json.loads(raw.decode("utf-8"))
        except Exception as err:
            raise Namel3ssError("Encrypted payload could not be decoded.") from err

    def wrap_encrypted(self, token: str) -> dict:
        return {ENCRYPTED_MARKER: token}

    def unwrap_encrypted(self, value: object) -> str | None:
        if isinstance(value, dict) and ENCRYPTED_MARKER in value:
            token = value.get(ENCRYPTED_MARKER)
            if isinstance(token, str) and token:
                return token
        return None


def load_encryption_service(
    project_root: str | Path | None,
    app_path: str | Path | None,
    *,
    required: bool,
) -> EncryptionService | None:
    config = load_security_config(project_root, app_path, required=False)
    if config is not None and not bool(config.encryption_enabled):
        if required:
            raise Namel3ssError(_encryption_disabled_message())
        return None
    algorithm = _normalize_algorithm(config.encryption_algorithm if config is not None else DEFAULT_ENCRYPTION_ALGORITHM)
    path = _key_path(project_root, app_path)
    if path is None or not path.exists():
        if required:
            raise Namel3ssError(_missing_key_message(path))
        return None
    key = _read_key(path)
    return EncryptionService(key=key, algorithm=algorithm)


def initialize_encryption_key(project_root: str | Path | None, app_path: str | Path | None) -> Path:
    path = _key_path(project_root, app_path)
    if path is None:
        raise Namel3ssError("Encryption key path could not be resolved.")
    if path.exists():
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = os.urandom(32)
    token = base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")
    path.write_text(token, encoding="utf-8")
    return path


def _key_path(project_root: str | Path | None, app_path: str | Path | None) -> Path | None:
    root = resolve_project_root(project_root, app_path)
    if root is None:
        return None
    name = slugify_text(root.name) or "app"
    return Path.home() / ".namel3ss" / "keys" / f"{name}.key"


def _read_key(path: Path) -> bytes:
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        raise Namel3ssError(_invalid_key_message(path))
    try:
        padded = raw + "=" * ((4 - len(raw) % 4) % 4)
        decoded = base64.urlsafe_b64decode(padded.encode("ascii"))
    except Exception:
        decoded = b""
    if not decoded:
        try:
            decoded = bytes.fromhex(raw)
        except Exception as err:
            raise Namel3ssError(_invalid_key_message(path)) from err
    digest = hashlib.sha256(decoded).digest()
    return digest


def _encrypt_bytes(key: bytes, payload: bytes, algorithm: str) -> str:
    normalized_algorithm = _normalize_algorithm(algorithm)
    cipher = AESCipher(key)
    nonce = hashlib.sha256(key + payload).digest()[:16]
    ciphertext = _ctr_crypt(cipher, nonce, payload)
    encoded = base64.urlsafe_b64encode(nonce + ciphertext).decode("ascii").rstrip("=")
    return f"{ENCRYPTION_PREFIX}{normalized_algorithm}:{encoded}"


def _decrypt_bytes(key: bytes, token: str, *, expected_algorithm: str | None = None) -> bytes:
    if not token.startswith(ENCRYPTION_PREFIX):
        raise Namel3ssError("Encrypted payload is missing a valid prefix.")
    encoded = token[len(ENCRYPTION_PREFIX) :]
    token_algorithm = None
    if ":" in encoded:
        maybe_algorithm, maybe_encoded = encoded.split(":", 1)
        normalized = maybe_algorithm.strip().lower()
        if normalized in SUPPORTED_ENCRYPTION_ALGORITHMS:
            token_algorithm = normalized
            encoded = maybe_encoded
    if expected_algorithm:
        normalized_expected = _normalize_algorithm(expected_algorithm)
        if token_algorithm is not None and token_algorithm != normalized_expected:
            raise Namel3ssError(_algorithm_mismatch_message(token_algorithm, normalized_expected))
    if token_algorithm is None and expected_algorithm:
        _normalize_algorithm(expected_algorithm)
    padded = encoded + "=" * ((4 - len(encoded) % 4) % 4)
    raw = base64.urlsafe_b64decode(padded.encode("ascii"))
    if len(raw) < 17:
        raise Namel3ssError("Encrypted payload is invalid.")
    nonce = raw[:16]
    ciphertext = raw[16:]
    cipher = AESCipher(key)
    return _ctr_crypt(cipher, nonce, ciphertext)


def _ctr_crypt(cipher: AESCipher, nonce: bytes, payload: bytes) -> bytes:
    out = bytearray()
    counter = int.from_bytes(nonce, "big")
    for offset in range(0, len(payload), 16):
        block = payload[offset : offset + 16]
        counter_block = counter.to_bytes(16, "big")
        keystream = cipher.encrypt_block(counter_block)
        out.extend(bytes(a ^ b for a, b in zip(block, keystream)))
        counter = (counter + 1) % (1 << 128)
    return bytes(out)


def _normalize_algorithm(value: object) -> str:
    text = str(value or "").strip().lower()
    if not text:
        text = DEFAULT_ENCRYPTION_ALGORITHM
    if text in SUPPORTED_ENCRYPTION_ALGORITHMS:
        return text
    raise Namel3ssError(_unsupported_algorithm_message(text))


def _missing_key_message(path: Path | None) -> str:
    hint = path.as_posix() if path else "~/.namel3ss/keys/<project>.key"
    return build_guidance_message(
        what="Sensitive flows require an encryption key.",
        why="No project encryption key was found.",
        fix="Create a key with n3 sensitive init-key.",
        example=f"Key path: {hint}",
    )


def _invalid_key_message(path: Path) -> str:
    return build_guidance_message(
        what="Encryption key is invalid.",
        why=f"Key at {path.as_posix()} could not be decoded.",
        fix="Replace the key with a base64 or hex value.",
        example="n3 sensitive init-key",
    )


def _unsupported_algorithm_message(value: str) -> str:
    allowed = ", ".join(SUPPORTED_ENCRYPTION_ALGORITHMS)
    return build_guidance_message(
        what=f"Encryption algorithm '{value}' is not supported.",
        why=f"Supported algorithms are {allowed}.",
        fix="Set security.yaml encryption.algorithm to a supported value.",
        example="encryption:\n  algorithm: aes-256-gcm",
    )


def _algorithm_mismatch_message(found: str, expected: str) -> str:
    return build_guidance_message(
        what="Encrypted payload algorithm does not match current security configuration.",
        why=f"Payload uses {found} while runtime expects {expected}.",
        fix="Use the same encryption algorithm for read/write operations.",
        example="security.yaml: encryption.algorithm: aes-256-gcm",
    )


def _encryption_disabled_message() -> str:
    return build_guidance_message(
        what="Encryption is disabled in security.yaml.",
        why="This flow requires encrypted persistence.",
        fix="Enable encryption in security.yaml or remove the security requirement.",
        example="encryption:\n  enabled: true",
    )


__all__ = [
    "EncryptionService",
    "ENCRYPTION_PREFIX",
    "ENCRYPTED_MARKER",
    "DEFAULT_ENCRYPTION_ALGORITHM",
    "SUPPORTED_ENCRYPTION_ALGORITHMS",
    "initialize_encryption_key",
    "load_encryption_service",
]
