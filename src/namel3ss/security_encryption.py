from __future__ import annotations

import base64
import hashlib
import os
from dataclasses import dataclass
from pathlib import Path

from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.persistence_paths import resolve_project_root
from namel3ss.utils.slugify import slugify_text
from namel3ss.crypto.aes import AESCipher


ENCRYPTION_PREFIX = "enc:v1:"
ENCRYPTED_MARKER = "__n3_encrypted__"


@dataclass(frozen=True)
class EncryptionService:
    key: bytes

    def encrypt_text(self, text: str) -> str:
        payload = text.encode("utf-8")
        token = _encrypt_bytes(self.key, payload)
        return token

    def decrypt_text(self, token: str) -> str:
        raw = _decrypt_bytes(self.key, token)
        return raw.decode("utf-8")

    def encrypt_json(self, value: object) -> str:
        payload = canonical_json_dumps(value, pretty=False, drop_run_keys=False).encode("utf-8")
        return _encrypt_bytes(self.key, payload)

    def decrypt_json(self, token: str) -> object:
        raw = _decrypt_bytes(self.key, token)
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
    path = _key_path(project_root, app_path)
    if path is None or not path.exists():
        if required:
            raise Namel3ssError(_missing_key_message(path))
        return None
    key = _read_key(path)
    return EncryptionService(key=key)


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


def _encrypt_bytes(key: bytes, payload: bytes) -> str:
    cipher = AESCipher(key)
    nonce = hashlib.sha256(key + payload).digest()[:16]
    ciphertext = _ctr_crypt(cipher, nonce, payload)
    encoded = base64.urlsafe_b64encode(nonce + ciphertext).decode("ascii").rstrip("=")
    return ENCRYPTION_PREFIX + encoded


def _decrypt_bytes(key: bytes, token: str) -> bytes:
    if not token.startswith(ENCRYPTION_PREFIX):
        raise Namel3ssError("Encrypted payload is missing a valid prefix.")
    encoded = token[len(ENCRYPTION_PREFIX) :]
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


__all__ = [
    "EncryptionService",
    "ENCRYPTION_PREFIX",
    "ENCRYPTED_MARKER",
    "initialize_encryption_key",
    "load_encryption_service",
]
