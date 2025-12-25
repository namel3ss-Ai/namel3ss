from __future__ import annotations

from pathlib import Path


PACKS_DIR = ".namel3ss/packs"
TRUST_DIR = ".namel3ss/trust"
PACK_MANIFEST = "pack.yaml"
PACK_SIGNATURE = "signature.txt"
PACK_BINDINGS = "tools.yaml"
PACK_VERIFICATION = "verification.json"
TRUST_KEYS = "keys.yaml"


def packs_root(app_root: Path) -> Path:
    return app_root / PACKS_DIR


def pack_path(app_root: Path, pack_id: str) -> Path:
    return packs_root(app_root) / pack_id


def pack_manifest_path(pack_dir: Path) -> Path:
    return pack_dir / PACK_MANIFEST


def pack_signature_path(pack_dir: Path) -> Path:
    return pack_dir / PACK_SIGNATURE


def pack_bindings_path(pack_dir: Path) -> Path:
    return pack_dir / PACK_BINDINGS


def pack_verification_path(pack_dir: Path) -> Path:
    return pack_dir / PACK_VERIFICATION


def trust_keys_path(app_root: Path) -> Path:
    return app_root / TRUST_DIR / TRUST_KEYS


__all__ = [
    "PACK_BINDINGS",
    "PACK_MANIFEST",
    "PACK_SIGNATURE",
    "PACK_VERIFICATION",
    "PACKS_DIR",
    "TRUST_KEYS",
    "TRUST_DIR",
    "pack_bindings_path",
    "pack_manifest_path",
    "pack_path",
    "pack_signature_path",
    "pack_verification_path",
    "packs_root",
    "trust_keys_path",
]
