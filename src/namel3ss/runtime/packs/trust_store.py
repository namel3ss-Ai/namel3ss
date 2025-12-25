from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.packs.layout import trust_keys_path


@dataclass(frozen=True)
class TrustedKey:
    key_id: str
    public_key: str


def load_trusted_keys(app_root: Path) -> list[TrustedKey]:
    path = trust_keys_path(app_root)
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    return _parse_keys_yaml(text, path)


def add_trusted_key(app_root: Path, key: TrustedKey) -> Path:
    path = trust_keys_path(app_root)
    keys = load_trusted_keys(app_root)
    if any(item.key_id == key.key_id for item in keys):
        raise Namel3ssError(
            build_guidance_message(
                what=f"Trusted key '{key.key_id}' already exists.",
                why="Key ids must be unique.",
                fix="Use a new key id or remove the old key.",
                example='n3 packs keys add --id "maintainer.alice" --public-key ./alice.pub',
            )
        )
    keys.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_render_keys_yaml(keys), encoding="utf-8")
    return path


def _parse_keys_yaml(text: str, path: Path) -> list[TrustedKey]:
    lines = text.splitlines()
    keys: list[TrustedKey] = []
    in_keys = False
    current: dict[str, str] | None = None
    for raw in lines:
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        if not in_keys:
            if indent == 0 and stripped == "trusted_keys:":
                in_keys = True
                continue
            raise Namel3ssError(_invalid_keys_message(path))
        if indent == 2 and stripped.startswith("- "):
            if current:
                keys.append(_build_key(current, path))
            current = {}
            entry = stripped[2:].strip()
            if entry:
                if ":" not in entry:
                    raise Namel3ssError(_invalid_keys_message(path))
                key, value = entry.split(":", 1)
                current[key.strip()] = _unquote(value.strip())
            continue
        if indent == 4 and current is not None:
            if ":" not in stripped:
                raise Namel3ssError(_invalid_keys_message(path))
            key, value = stripped.split(":", 1)
            current[key.strip()] = _unquote(value.strip())
            continue
        raise Namel3ssError(_invalid_keys_message(path))
    if current:
        keys.append(_build_key(current, path))
    if not in_keys:
        raise Namel3ssError(_invalid_keys_message(path))
    return keys


def _build_key(data: dict[str, str], path: Path) -> TrustedKey:
    key_id = data.get("id")
    public_key = data.get("public_key")
    if not key_id or not public_key:
        raise Namel3ssError(_invalid_keys_message(path))
    return TrustedKey(key_id=key_id, public_key=public_key)


def _render_keys_yaml(keys: list[TrustedKey]) -> str:
    lines = ["trusted_keys:"]
    for key in keys:
        lines.append(f'  - id: "{_escape(key.key_id)}"')
        lines.append(f'    public_key: "{_escape(key.public_key)}"')
    return "\n".join(lines) + "\n"


def _invalid_keys_message(path: Path) -> str:
    return build_guidance_message(
        what="Trusted keys file is invalid.",
        why=f"Expected trusted_keys in {path.as_posix()}.",
        fix="Rewrite the keys file or re-add keys.",
        example='trusted_keys:\\n  - id: "maintainer.alice"\\n    public_key: "sha256:..."',
    )


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        inner = value[1:-1]
        return inner.replace('\\"', '"').replace("\\\\", "\\")
    return value


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


__all__ = ["TrustedKey", "add_trusted_key", "load_trusted_keys"]
