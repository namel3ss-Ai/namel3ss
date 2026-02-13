from __future__ import annotations

from dataclasses import dataclass
import hashlib
from importlib import resources as importlib_resources
import json
from pathlib import Path
import re

from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.ui.renderer.manifest_loader import (
    load_renderer_manifest_json,
    renderer_manifest_resource_path,
)


RENDERER_MANIFEST_PARITY_ERROR_CODE = "N3E_RENDERER_MANIFEST_PARITY_INVALID"
_MANIFEST_EXTRACT_PATTERN = re.compile(
    r"const\s+MANIFEST\s*=\s*(\{[\s\S]*?\})\s*;\s*const\s+REQUIRED_RENDERERS",
    re.MULTILINE,
)


@dataclass(frozen=True)
class RendererManifestParityResult:
    ok: bool
    error_code: str
    error_message: str
    manifest_hash: str
    registry_manifest_hash: str
    manifest_path: str
    registry_path: str
    renderer_count: int

    def to_dict(self) -> dict[str, object]:
        return {
            "error_code": self.error_code,
            "error_message": self.error_message,
            "manifest_hash": self.manifest_hash,
            "manifest_path": self.manifest_path,
            "ok": bool(self.ok),
            "registry_manifest_hash": self.registry_manifest_hash,
            "registry_path": self.registry_path,
            "renderer_count": int(self.renderer_count),
        }


def verify_renderer_manifest_parity(
    *,
    manifest_json: dict[str, object] | None = None,
    manifest_path: Path | None = None,
    registry_script_path: Path | None = None,
) -> RendererManifestParityResult:
    resolved_manifest_path = _resolve_manifest_path(manifest_path)
    resolved_registry_path = _resolve_registry_path(registry_script_path)

    manifest_payload = manifest_json if isinstance(manifest_json, dict) else _load_manifest_payload(manifest_path)
    if not isinstance(manifest_payload, dict):
        return _error_result(
            message="renderer manifest payload is invalid.",
            manifest_path=resolved_manifest_path,
            registry_path=resolved_registry_path,
        )

    script_text = _load_registry_script_text(registry_script_path)
    if script_text is None:
        return _error_result(
            message="renderer registry script is missing or unreadable.",
            manifest_path=resolved_manifest_path,
            registry_path=resolved_registry_path,
        )

    registry_manifest = _extract_manifest_from_registry_script(script_text)
    if not isinstance(registry_manifest, dict):
        return _error_result(
            message="renderer registry script manifest is invalid.",
            manifest_path=resolved_manifest_path,
            registry_path=resolved_registry_path,
        )

    manifest_hash = _stable_hash(manifest_payload)
    registry_hash = _stable_hash(registry_manifest)
    if manifest_hash != registry_hash:
        return RendererManifestParityResult(
            ok=False,
            error_code=RENDERER_MANIFEST_PARITY_ERROR_CODE,
            error_message="renderer manifest and renderer registry script are out of sync.",
            manifest_hash=manifest_hash,
            registry_manifest_hash=registry_hash,
            manifest_path=resolved_manifest_path,
            registry_path=resolved_registry_path,
            renderer_count=_renderer_count(manifest_payload),
        )

    return RendererManifestParityResult(
        ok=True,
        error_code="",
        error_message="",
        manifest_hash=manifest_hash,
        registry_manifest_hash=registry_hash,
        manifest_path=resolved_manifest_path,
        registry_path=resolved_registry_path,
        renderer_count=_renderer_count(manifest_payload),
    )


def require_renderer_manifest_parity(
    *,
    manifest_json: dict[str, object] | None = None,
    manifest_path: Path | None = None,
    registry_script_path: Path | None = None,
) -> RendererManifestParityResult:
    result = verify_renderer_manifest_parity(
        manifest_json=manifest_json,
        manifest_path=manifest_path,
        registry_script_path=registry_script_path,
    )
    if result.ok:
        return result
    raise Namel3ssError(
        build_guidance_message(
            what=f"{RENDERER_MANIFEST_PARITY_ERROR_CODE}: renderer registry parity check failed.",
            why=result.error_message or "Renderer manifest and registry script do not match.",
            fix="Regenerate renderer registry assets and restart runtime.",
            example="python tools/build_renderer_manifest.py",
        ),
        details={"error_code": RENDERER_MANIFEST_PARITY_ERROR_CODE, "category": "engine"},
    )


def renderer_registry_script_resource_path() -> Path:
    resource = importlib_resources.files("namel3ss").joinpath("studio", "web", "renderer_registry.js")
    try:
        return Path(resource)
    except TypeError:
        with importlib_resources.as_file(resource) as resolved:
            return Path(resolved)


def _load_manifest_payload(path: Path | None) -> dict[str, object] | None:
    try:
        payload = load_renderer_manifest_json(path=path)
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def _load_registry_script_text(path: Path | None) -> str | None:
    try:
        if path is not None:
            return path.read_text(encoding="utf-8")
        resource = importlib_resources.files("namel3ss").joinpath("studio", "web", "renderer_registry.js")
        return resource.read_text(encoding="utf-8")
    except Exception:
        return None


def _extract_manifest_from_registry_script(script_text: str) -> dict[str, object] | None:
    match = _MANIFEST_EXTRACT_PATTERN.search(script_text or "")
    if match is None:
        return None
    raw_manifest = str(match.group(1) or "").strip()
    if not raw_manifest:
        return None
    try:
        parsed = json.loads(raw_manifest)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _stable_hash(payload: dict[str, object]) -> str:
    encoded = canonical_json_dumps(payload, pretty=False, drop_run_keys=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _resolve_manifest_path(path: Path | None) -> str:
    resolved = path if isinstance(path, Path) else renderer_manifest_resource_path()
    return Path(resolved).as_posix()


def _resolve_registry_path(path: Path | None) -> str:
    resolved = path if isinstance(path, Path) else renderer_registry_script_resource_path()
    return Path(resolved).as_posix()


def _renderer_count(payload: dict[str, object]) -> int:
    renderers = payload.get("renderers")
    if not isinstance(renderers, list):
        return 0
    return len([item for item in renderers if isinstance(item, dict)])


def _error_result(*, message: str, manifest_path: str, registry_path: str) -> RendererManifestParityResult:
    return RendererManifestParityResult(
        ok=False,
        error_code=RENDERER_MANIFEST_PARITY_ERROR_CODE,
        error_message=message,
        manifest_hash="",
        registry_manifest_hash="",
        manifest_path=manifest_path,
        registry_path=registry_path,
        renderer_count=0,
    )


__all__ = [
    "RENDERER_MANIFEST_PARITY_ERROR_CODE",
    "RendererManifestParityResult",
    "renderer_registry_script_resource_path",
    "require_renderer_manifest_parity",
    "verify_renderer_manifest_parity",
]
