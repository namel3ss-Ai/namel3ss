from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys

from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.ingestion.gate_contract import gate_signature_payload
from namel3ss.runtime.native import loader as native_loader
from namel3ss.runtime.native.status import NativeStatus, status_to_code


def run_doc_command(args: list[str] | None = None) -> int:
    args = [] if args is None else list(args)
    json_only = {"--json"}
    extra = [arg for arg in args if arg not in json_only]
    if extra:
        raise Namel3ssError(
            build_guidance_message(
                what=f"Unknown doc arguments: {' '.join(extra)}.",
                why="doc is a deterministic runtime report and accepts only --json.",
                fix="Remove unsupported flags.",
                example="n3 doc",
            )
        )
    payload = build_doc_payload()
    text = canonical_json_dumps(payload, pretty=True, drop_run_keys=False)
    sys.stdout.write(text)
    return 0


def build_doc_payload() -> dict:
    cache_kind = _persistence_kind(Path.cwd())
    return {
        "runtime_signature": _runtime_signature(),
        "native": _native_payload(),
        "pack_governance": _pack_payload(),
        "ingestion_gate": {
            "enabled": True,
            "cache_root": cache_kind,
            "quarantine_root": cache_kind,
        },
        "python": _python_payload(),
    }


def _runtime_signature() -> str:
    payload = {
        "ingestion_gate": gate_signature_payload(),
        "pack_governance": _pack_payload(),
        "native_status": _native_status_payload(),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _native_status_payload() -> dict:
    items = []
    for status in NativeStatus:
        items.append(
            {
                "name": status.name,
                "value": int(status.value),
                "error_code": status_to_code(status),
            }
        )
    return {"status_codes": items}


def _native_payload() -> dict:
    return {
        "enabled": native_loader.native_enabled(),
        "available": native_loader.native_available(),
        "artifact": _native_artifact(),
    }


def _native_artifact() -> str:
    lib_env = os.getenv("N3_NATIVE_LIB", "").strip()
    if lib_env:
        return "env"
    if native_loader.native_library_path() is not None:
        return "package"
    return "missing"


def _pack_payload() -> dict:
    return {
        "allowlist": {"enabled": True},
        "signing": {"enabled": True},
    }


def _python_payload() -> dict:
    version = f"{sys.version_info.major}"
    return {"version": version}


def _persistence_kind(project_root: Path | None) -> str:
    env_value = os.getenv("N3_PERSIST_ROOT", "").strip()
    if env_value:
        return "env_root"
    if project_root is None:
        return "unresolved"
    if _is_writable_dir(project_root):
        return "project_root"
    return "temp_fallback"


def _is_writable_dir(path: Path) -> bool:
    try:
        return path.is_dir() and os.access(path, os.W_OK | os.X_OK)
    except Exception:
        return False


__all__ = ["build_doc_payload", "run_doc_command"]
