from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message


SPEC_VERSIONS_PATH = Path(__file__).resolve().parents[2] / "resources" / "spec_versions.json"
REQUIRED_SPEC_KEYS = {
    "language_core",
    "tool_dsl",
    "tool_protocol",
    "pack_manifest",
    "bindings_schema",
    "runner_contract",
    "ui_manifest",
    "identity_schema",
    "persistence_contract",
    "trace_schema",
}


def spec_versions_path() -> Path:
    return SPEC_VERSIONS_PATH


@lru_cache(maxsize=1)
def load_spec_versions(path: Path | None = None) -> dict[str, int]:
    target = path or SPEC_VERSIONS_PATH
    if not target.exists():
        raise Namel3ssError(
            build_guidance_message(
                what="Spec versions file is missing.",
                why=f"Expected {target.as_posix()} to exist.",
                fix="Restore resources/spec_versions.json.",
                example="git checkout -- resources/spec_versions.json",
            )
        )
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError as err:
        raise Namel3ssError(
            build_guidance_message(
                what="Spec versions file is not valid JSON.",
                why=f"JSON parsing failed: {err.msg}.",
                fix="Fix resources/spec_versions.json.",
                example='{"language_core": 1, "tool_dsl": 1, "tool_protocol": 1}',
            )
        ) from err
    if not isinstance(data, dict):
        raise Namel3ssError(
            build_guidance_message(
                what="Spec versions file is invalid.",
                why="Expected a JSON object at the top level.",
                fix="Replace the file with a key/value JSON object.",
                example='{"language_core": 1, "tool_dsl": 1, "tool_protocol": 1}',
            )
        )
    keys = set(data.keys())
    missing = sorted(REQUIRED_SPEC_KEYS - keys)
    extra = sorted(keys - REQUIRED_SPEC_KEYS)
    if missing or extra:
        details = []
        if missing:
            details.append(f"missing: {', '.join(missing)}")
        if extra:
            details.append(f"extra: {', '.join(extra)}")
        raise Namel3ssError(
            build_guidance_message(
                what="Spec versions file keys are out of sync.",
                why="; ".join(details) if details else "Unexpected spec versions keys.",
                fix="Update resources/spec_versions.json to match the required keys.",
                example="resources/spec_versions.json",
            )
        )
    normalized: dict[str, int] = {}
    for key in REQUIRED_SPEC_KEYS:
        value = data.get(key)
        if not isinstance(value, int):
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Spec version '{key}' is invalid.",
                    why="Versions must be integers.",
                    fix="Set the value to an integer version.",
                    example=f'"{key}": 1',
                )
            )
        normalized[key] = value
    return normalized


__all__ = ["SPEC_VERSIONS_PATH", "REQUIRED_SPEC_KEYS", "load_spec_versions", "spec_versions_path"]
