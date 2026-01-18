from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.packs.layout import pack_signature_path, pack_verification_path
from namel3ss.runtime.packs.manifest import parse_pack_manifest_text
from namel3ss.runtime.packs.signature import DEFAULT_ALGORITHM, LEGACY_ALGORITHM, parse_signature_text, verify_signature
from namel3ss.runtime.packs.trust_store import TrustedKey, load_trusted_keys


@dataclass(frozen=True)
class PackVerification:
    pack_id: str
    version: str
    digest: str
    verified: bool
    key_id: str | None
    verified_at: str | None


VERIFIED_AT_PLACEHOLDER = "not_recorded"


def compute_pack_digest(manifest_text: str, tools_text: str | None) -> str:
    normalized = _normalize_text(_strip_signing_fields(manifest_text))
    if tools_text is not None:
        normalized = f"{normalized}\n{_normalize_text(tools_text)}"
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def verify_pack(
    app_root: Path,
    pack_id: str,
    version: str,
    manifest_text: str,
    tools_text: str | None,
    pack_dir: Path,
) -> PackVerification:
    verification, reason = _assess_pack_signature(
        app_root=app_root,
        pack_id=pack_id,
        version=version,
        manifest_text=manifest_text,
        tools_text=tools_text,
        pack_dir=pack_dir,
    )
    if not verification.verified:
        if reason == "missing_signer_id":
            raise Namel3ssError(_missing_signer_id_message(pack_id))
        if reason == "missing_signature":
            raise Namel3ssError(_missing_signature_message(pack_id))
        if reason == "unsupported_signature":
            raise Namel3ssError(_unsupported_signature_message(pack_id))
        if reason == "signature_mismatch":
            raise Namel3ssError(_signature_mismatch_message(pack_id))
        if reason == "untrusted_signature":
            raise Namel3ssError(_untrusted_signature_message(pack_id))
        raise Namel3ssError(_signature_mismatch_message(pack_id))
    _write_verification(pack_dir, verification)
    return verification


def load_pack_verification(
    pack_dir: Path,
    manifest_text: str,
    tools_text: str | None,
    *,
    app_root: Path | None = None,
) -> PackVerification:
    digest = compute_pack_digest(manifest_text, tools_text)
    if app_root is not None:
        verification, _ = _assess_pack_signature(
            app_root=app_root,
            pack_id="",
            version="",
            manifest_text=manifest_text,
            tools_text=tools_text,
            pack_dir=pack_dir,
        )
        return PackVerification(
            pack_id=verification.pack_id,
            version=verification.version,
            digest=digest,
            verified=verification.verified,
            key_id=verification.key_id,
            verified_at=verification.verified_at,
        )
    path = pack_verification_path(pack_dir)
    if not path.exists():
        return PackVerification(
            pack_id="",
            version="",
            digest=digest,
            verified=False,
            key_id=None,
            verified_at=None,
        )
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return PackVerification(
            pack_id="",
            version="",
            digest=digest,
            verified=False,
            key_id=None,
            verified_at=None,
        )
    verified = bool(data.get("verified")) and data.get("digest") == digest
    return PackVerification(
        pack_id=str(data.get("pack_id") or ""),
        version=str(data.get("version") or ""),
        digest=digest,
        verified=verified,
        key_id=str(data.get("key_id") or "") if data.get("key_id") else None,
        verified_at=str(data.get("verified_at") or "") if data.get("verified_at") else None,
    )


def _read_signature(pack_dir: Path) -> str | None:
    path = pack_signature_path(pack_dir)
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return None
    return text


def _assess_pack_signature(
    *,
    app_root: Path,
    pack_id: str,
    version: str,
    manifest_text: str,
    tools_text: str | None,
    pack_dir: Path,
) -> tuple[PackVerification, str | None]:
    digest = compute_pack_digest(manifest_text, tools_text)
    signature_text = _read_signature(pack_dir)
    if signature_text is None:
        return _unverified(pack_id, version, digest), "missing_signature"
    signature = parse_signature_text(signature_text)
    if signature is None:
        return _unverified(pack_id, version, digest), "missing_signature"
    if signature.algorithm not in {DEFAULT_ALGORITHM, LEGACY_ALGORITHM}:
        return _unverified(pack_id, version, digest), "unsupported_signature"
    manifest = _parse_manifest(manifest_text, pack_dir)
    signer_id = manifest.signer_id if manifest else None
    if not signer_id:
        return _unverified(pack_id, version, digest), "missing_signer_id"
    trusted = load_trusted_keys(app_root)
    key = _match_trusted_key(signer_id, trusted)
    if key is None:
        return _unverified(pack_id, version, digest), "untrusted_signature"
    if not verify_signature(digest, signature_text, key.public_key):
        return _unverified(pack_id, version, digest), "signature_mismatch"
    verification = PackVerification(
        pack_id=manifest.pack_id if manifest else pack_id,
        version=manifest.version if manifest else version,
        digest=digest,
        verified=True,
        key_id=key.key_id,
        verified_at=VERIFIED_AT_PLACEHOLDER,
    )
    return verification, None


def _unverified(pack_id: str, version: str, digest: str) -> PackVerification:
    return PackVerification(
        pack_id=pack_id,
        version=version,
        digest=digest,
        verified=False,
        key_id=None,
        verified_at=None,
    )


def _parse_manifest(manifest_text: str, pack_dir: Path):
    try:
        return parse_pack_manifest_text(manifest_text, pack_dir / "pack.yaml")
    except Exception:
        return None


def _match_trusted_key(signer_id: str, keys: list[TrustedKey]) -> TrustedKey | None:
    for key in keys:
        if key.key_id == signer_id:
            return key
    return None


def _write_verification(pack_dir: Path, verification: PackVerification) -> None:
    payload = {
        "pack_id": verification.pack_id,
        "version": verification.version,
        "digest": verification.digest,
        "verified": verification.verified,
        "key_id": verification.key_id,
        "verified_at": verification.verified_at,
    }
    path = pack_verification_path(pack_dir)
    path.write_text(canonical_json_dumps(payload, pretty=True), encoding="utf-8")


def _normalize_text(text: str) -> str:
    return "\n".join(line.rstrip() for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")).strip()


def _strip_signing_fields(text: str) -> str:
    lines: list[str] = []
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            lines.append(raw)
            continue
        if raw.lstrip() != raw:
            lines.append(raw)
            continue
        if ":" not in stripped:
            lines.append(raw)
            continue
        key = stripped.split(":", 1)[0].strip()
        if key in {"signer_id", "signed_at", "digest"}:
            continue
        lines.append(raw)
    return "\n".join(lines)


def _missing_signature_message(pack_id: str) -> str:
    return build_guidance_message(
        what=f'Pack "{pack_id}" is missing a signature.',
        why="signature.txt is required to verify a pack.",
        fix="Add signature.txt or use a trusted pack source.",
        example="signature.txt",
    )


def _missing_signer_id_message(pack_id: str) -> str:
    return build_guidance_message(
        what=f'Pack "{pack_id}" is missing signer metadata.',
        why="signer_id is required to verify a pack.",
        fix="Re-sign the pack to add signer_id.",
        example='n3 packs sign ./pack --key-id "maintainer.alice" --private-key ./alice.key',
    )


def _unsupported_signature_message(pack_id: str) -> str:
    return build_guidance_message(
        what=f'Pack "{pack_id}" signature is unsupported.',
        why="The signature algorithm is not recognized.",
        fix="Re-sign the pack with the supported signing flow.",
        example='n3 packs sign ./pack --key-id "maintainer.alice" --private-key ./alice.key',
    )


def _signature_mismatch_message(pack_id: str) -> str:
    return build_guidance_message(
        what=f'Pack "{pack_id}" signature does not match.',
        why="The signature digest does not match pack.yaml/tools.yaml.",
        fix="Re-sign the pack after updating its files.",
        example="signature.txt",
    )


def _untrusted_signature_message(pack_id: str) -> str:
    return build_guidance_message(
        what=f'Pack "{pack_id}" signature is untrusted.',
        why="No trusted key matches the signature digest.",
        fix="Add the signer to .namel3ss/trust/keys.yaml.",
        example='n3 packs keys add --id "maintainer.alice" --public-key ./alice.pub',
    )


__all__ = ["PackVerification", "compute_pack_digest", "load_pack_verification", "verify_pack"]
