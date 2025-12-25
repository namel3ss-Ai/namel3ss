from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.packs.layout import pack_bindings_path, pack_signature_path
from namel3ss.runtime.packs.manifest import parse_pack_manifest
from namel3ss.runtime.packs.verification import compute_pack_digest


@dataclass(frozen=True)
class PackSignResult:
    pack_id: str
    version: str
    digest: str
    signer_id: str
    signed_at: str
    signature_path: Path
    manifest_path: Path


def sign_pack(pack_dir: Path, *, key_id: str, private_key_path: Path) -> PackSignResult:
    if not key_id.strip():
        raise Namel3ssError(_missing_key_id_message())
    if not private_key_path.exists():
        raise Namel3ssError(_missing_private_key_message(private_key_path))
    key_text = private_key_path.read_text(encoding="utf-8").strip()
    if not key_text:
        raise Namel3ssError(_empty_private_key_message(private_key_path))
    manifest_path = pack_dir / "pack.yaml"
    if not manifest_path.exists():
        raise Namel3ssError(_missing_manifest_message(manifest_path))
    manifest = parse_pack_manifest(manifest_path)
    manifest_text = manifest_path.read_text(encoding="utf-8")
    tools_text = None
    bindings_path = pack_bindings_path(pack_dir)
    if bindings_path.exists():
        tools_text = bindings_path.read_text(encoding="utf-8")
    digest = compute_pack_digest(manifest_text, tools_text)
    signature_path = pack_signature_path(pack_dir)
    signature_path.write_text(digest + "\n", encoding="utf-8")
    signed_at = _utc_now()
    updated = _update_signing_fields(manifest_text, key_id, signed_at, digest)
    manifest_path.write_text(updated, encoding="utf-8")
    return PackSignResult(
        pack_id=manifest.pack_id,
        version=manifest.version,
        digest=digest,
        signer_id=key_id,
        signed_at=signed_at,
        signature_path=signature_path,
        manifest_path=manifest_path,
    )


def _update_signing_fields(text: str, signer_id: str, signed_at: str, digest: str) -> str:
    lines = []
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
    lines.append(f'signer_id: "{_escape(signer_id)}"')
    lines.append(f'signed_at: "{signed_at}"')
    lines.append(f'digest: "{digest}"')
    return "\n".join(lines).rstrip() + "\n"


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _missing_key_id_message() -> str:
    return build_guidance_message(
        what="Signer id is missing.",
        why="You must provide --key-id.",
        fix="Pass --key-id with a signer id.",
        example='n3 packs sign ./pack --key-id "maintainer.alice" --private-key ./alice.key',
    )


def _missing_private_key_message(path: Path) -> str:
    return build_guidance_message(
        what="Private key file was not found.",
        why=f"Expected {path.as_posix()} to exist.",
        fix="Provide a valid private key file path.",
        example='n3 packs sign ./pack --key-id "maintainer.alice" --private-key ./alice.key',
    )


def _empty_private_key_message(path: Path) -> str:
    return build_guidance_message(
        what="Private key file is empty.",
        why=f"No data found in {path.as_posix()}.",
        fix="Provide a valid private key file.",
        example='n3 packs sign ./pack --key-id "maintainer.alice" --private-key ./alice.key',
    )


def _missing_manifest_message(path: Path) -> str:
    return build_guidance_message(
        what="Pack manifest is missing.",
        why=f"Expected {path.as_posix()} to exist.",
        fix="Provide a valid pack directory.",
        example="pack.yaml",
    )


__all__ = ["PackSignResult", "sign_pack"]
