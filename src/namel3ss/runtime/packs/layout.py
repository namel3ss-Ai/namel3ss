from __future__ import annotations

from pathlib import Path


PACKS_DIR = ".namel3ss/packs"
TRUST_DIR = ".namel3ss/trust"
PACK_MANIFEST = "pack.yaml"
PACK_SIGNATURE = "signature.txt"
PACK_BINDINGS = "tools.yaml"
PACK_CAPABILITIES = "capabilities.yaml"
PACK_INTENT = "intent.md"
PACK_VERIFICATION = "verification.json"
TRUST_KEYS = "keys.yaml"
TRUST_POLICY = "policy.toml"
PACK_SOURCE_META = ".n3pack_source.json"


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


def pack_capabilities_path(pack_dir: Path) -> Path:
    return pack_dir / PACK_CAPABILITIES


def pack_intent_path(pack_dir: Path) -> Path:
    return pack_dir / PACK_INTENT


def pack_verification_path(pack_dir: Path) -> Path:
    return pack_dir / PACK_VERIFICATION


def pack_source_meta_path(pack_dir: Path) -> Path:
    return pack_dir / PACK_SOURCE_META


def trust_keys_path(app_root: Path) -> Path:
    return app_root / TRUST_DIR / TRUST_KEYS


def trust_policy_path(app_root: Path) -> Path:
    return app_root / TRUST_DIR / TRUST_POLICY


__all__ = [
    "PACK_BINDINGS",
    "PACK_CAPABILITIES",
    "PACK_INTENT",
    "PACK_MANIFEST",
    "PACK_SIGNATURE",
    "PACK_VERIFICATION",
    "PACKS_DIR",
    "PACK_SOURCE_META",
    "TRUST_KEYS",
    "TRUST_POLICY",
    "TRUST_DIR",
    "pack_bindings_path",
    "pack_capabilities_path",
    "pack_intent_path",
    "pack_manifest_path",
    "pack_path",
    "pack_signature_path",
    "pack_source_meta_path",
    "pack_verification_path",
    "packs_root",
    "trust_keys_path",
    "trust_policy_path",
]
