from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message


@dataclass(frozen=True)
class TrustedExtensionRecord:
    name: str
    version: str
    hash: str
    trusted_at: str
    permissions: tuple[str, ...]
    author: str

    def to_payload(self) -> dict[str, object]:
        return {
            "name": self.name,
            "version": self.version,
            "hash": self.hash,
            "trusted_at": self.trusted_at,
            "permissions": list(self.permissions),
            "author": self.author,
        }


def trust_store_path(project_root: str | Path) -> Path:
    return Path(project_root).resolve() / ".namel3ss" / "trusted_extensions.yaml"


def compute_tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted([item for item in root.rglob("*") if item.is_file()], key=lambda p: p.as_posix()):
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def load_trusted_extensions(project_root: str | Path) -> list[TrustedExtensionRecord]:
    path = trust_store_path(project_root)
    if not path.exists():
        return []
    return _parse_trust_yaml(path.read_text(encoding="utf-8"), path)


def save_trusted_extensions(project_root: str | Path, records: list[TrustedExtensionRecord]) -> Path:
    path = trust_store_path(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["trusted_extensions:"]
    for record in sorted(records, key=lambda item: (item.name, item.version, item.hash)):
        lines.append(f'  - name: "{_escape(record.name)}"')
        lines.append(f'    version: "{_escape(record.version)}"')
        lines.append(f'    hash: "{_escape(record.hash)}"')
        lines.append(f'    trusted_at: "{_escape(record.trusted_at)}"')
        lines.append(f'    author: "{_escape(record.author)}"')
        if record.permissions:
            lines.append("    permissions:")
            for permission in record.permissions:
                lines.append(f'      - "{_escape(permission)}"')
        else:
            lines.append("    permissions: []")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def trust_extension(
    project_root: str | Path,
    *,
    name: str,
    version: str,
    digest: str,
    permissions: tuple[str, ...],
    author: str,
) -> TrustedExtensionRecord:
    records = load_trusted_extensions(project_root)
    retained = [
        item
        for item in records
        if not (item.name == name and item.version == version)
    ]
    record = TrustedExtensionRecord(
        name=name,
        version=version,
        hash=digest,
        trusted_at=datetime.now(timezone.utc).isoformat(),
        permissions=tuple(permissions),
        author=str(author or "unknown"),
    )
    retained.append(record)
    save_trusted_extensions(project_root, retained)
    return record


def revoke_extension(project_root: str | Path, *, name: str, version: str | None = None) -> int:
    records = load_trusted_extensions(project_root)
    retained: list[TrustedExtensionRecord] = []
    removed = 0
    for record in records:
        matches_name = record.name == name
        matches_version = version is None or record.version == version
        if matches_name and matches_version:
            removed += 1
            continue
        retained.append(record)
    save_trusted_extensions(project_root, retained)
    return removed


def is_extension_trusted(
    project_root: str | Path,
    *,
    name: str,
    version: str,
    digest: str,
) -> bool:
    for record in load_trusted_extensions(project_root):
        if record.name == name and record.version == version and record.hash == digest:
            return True
    return False


def _parse_trusted_record(item: object, *, idx: int, path: Path) -> TrustedExtensionRecord:
    if not isinstance(item, dict):
        raise Namel3ssError(_invalid_trust_store_message(path))
    name = item.get("name")
    version = item.get("version")
    digest = item.get("hash")
    trusted_at = item.get("trusted_at")
    author = item.get("author")
    if not isinstance(name, str) or not name.strip():
        raise Namel3ssError(_invalid_trust_store_item_message(path, idx, "name"))
    if not isinstance(version, str) or not version.strip():
        raise Namel3ssError(_invalid_trust_store_item_message(path, idx, "version"))
    if not isinstance(digest, str) or not digest.strip():
        raise Namel3ssError(_invalid_trust_store_item_message(path, idx, "hash"))
    if not isinstance(trusted_at, str) or not trusted_at.strip():
        raise Namel3ssError(_invalid_trust_store_item_message(path, idx, "trusted_at"))
    if not isinstance(author, str) or not author.strip():
        raise Namel3ssError(_invalid_trust_store_item_message(path, idx, "author"))
    permissions_value = item.get("permissions", [])
    if not isinstance(permissions_value, list):
        raise Namel3ssError(_invalid_trust_store_item_message(path, idx, "permissions"))
    permissions: list[str] = []
    for permission in permissions_value:
        if not isinstance(permission, str) or not permission.strip():
            raise Namel3ssError(_invalid_trust_store_item_message(path, idx, "permissions"))
        permissions.append(permission.strip().lower())
    return TrustedExtensionRecord(
        name=name.strip(),
        version=version.strip(),
        hash=digest.strip(),
        trusted_at=trusted_at.strip(),
        permissions=tuple(permissions),
        author=author.strip(),
    )


def _parse_trust_yaml(text: str, path: Path) -> list[TrustedExtensionRecord]:
    lines = text.splitlines()
    in_root = False
    current: dict[str, object] | None = None
    records: list[TrustedExtensionRecord] = []
    for raw in lines:
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        if not in_root:
            if indent == 0 and stripped == "trusted_extensions:":
                in_root = True
                continue
            raise Namel3ssError(_invalid_trust_store_message(path))
        if indent == 2 and stripped.startswith("- "):
            if current:
                records.append(_parse_trusted_record(current, idx=len(records), path=path))
            current = {}
            inline = stripped[2:].strip()
            if inline:
                key, value = _split_mapping(inline, path)
                current[key] = _unquote(value)
            continue
        if indent == 4 and current is not None:
            key, value = _split_mapping(stripped, path)
            if key == "permissions":
                if value not in {"", "[]"}:
                    raise Namel3ssError(_invalid_trust_store_item_message(path, len(records), "permissions"))
                current["permissions"] = []
            else:
                current[key] = _unquote(value)
            continue
        if indent == 6 and current is not None and stripped.startswith("- "):
            permissions = current.get("permissions")
            if not isinstance(permissions, list):
                raise Namel3ssError(_invalid_trust_store_item_message(path, len(records), "permissions"))
            permissions.append(_unquote(stripped[2:].strip()))
            continue
        raise Namel3ssError(_invalid_trust_store_message(path))
    if current:
        records.append(_parse_trusted_record(current, idx=len(records), path=path))
    if not in_root:
        raise Namel3ssError(_invalid_trust_store_message(path))
    return records


def _invalid_trust_store_message(path: Path) -> str:
    return build_guidance_message(
        what=f"Trust store file is invalid: {path.as_posix()}",
        why='Expected a mapping with "trusted_extensions".',
        fix="Recreate trust entries with CLI commands.",
        example='n3 plugin trust charts@0.1.0 --yes',
    )


def _invalid_trust_store_item_message(path: Path, idx: int, field: str) -> str:
    return build_guidance_message(
        what=f"Trust store entry {idx} is invalid.",
        why=f"Field '{field}' is missing or invalid in {path.as_posix()}.",
        fix="Revoke and trust the extension again.",
        example='n3 plugin revoke charts && n3 plugin trust charts@0.1.0 --yes',
    )


def _escape(value: str) -> str:
    return str(value).replace("\\", "\\\\").replace('"', '\\"')


def _unquote(value: str) -> str:
    text = str(value)
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {'"', "'"}:
        inner = text[1:-1]
        return inner.replace('\\"', '"').replace("\\\\", "\\")
    return text


def _split_mapping(value: str, path: Path) -> tuple[str, str]:
    if ":" not in value:
        raise Namel3ssError(_invalid_trust_store_message(path))
    key, raw = value.split(":", 1)
    return key.strip(), raw.strip()


__all__ = [
    "TrustedExtensionRecord",
    "compute_tree_hash",
    "is_extension_trusted",
    "load_trusted_extensions",
    "revoke_extension",
    "save_trusted_extensions",
    "trust_extension",
    "trust_store_path",
]
