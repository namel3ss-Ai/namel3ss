from __future__ import annotations

import json
from pathlib import Path


def stable_join(items: list[str], sep: str = ", ") -> str:
    return sep.join(items)


def stable_bullets(lines: list[str]) -> list[str]:
    return [line if line.startswith("- ") else f"- {line}" for line in lines]


def stable_truncate(text: str, limit: int = 120) -> str:
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def build_plain_text(pack: dict) -> str:
    lines: list[str] = []
    lines.append(f"summary: {pack.get('summary') or ''}")
    lines.append(f"api_version: {pack.get('api_version') or ''}")
    lines.append(f"build_id: {pack.get('build_id') or ''}")
    lines.append(f"created_at: {pack.get('created_at') or ''}")
    inputs = pack.get("inputs") or {}
    lines.append(f"source_fingerprint: {inputs.get('source_fingerprint')}")
    files = inputs.get("files") or []
    lines.append(f"files.count: {len(files)}")
    config = inputs.get("config") or {}
    tools = config.get("tool_bindings") or {}
    lines.append(f"tool_bindings.count: {tools.get('count')}")
    overrides = config.get("capability_overrides") or {}
    lines.append(f"capability_overrides.count: {overrides.get('count')}")

    guarantees = pack.get("guarantees") or []
    lines.append(f"guarantees.count: {len(guarantees)}")
    for idx, item in enumerate(guarantees, start=1):
        lines.append(f"guarantee.{idx}: {item}")

    constraints = pack.get("constraints") or []
    lines.append(f"constraints.count: {len(constraints)}")
    for idx, item in enumerate(constraints, start=1):
        lines.append(f"constraint.{idx}: {item}")

    components = pack.get("components") or {}
    lines.append(f"components.memory: {components.get('memory')}")
    lines.append(f"components.execution: {components.get('execution')}")
    lines.append(f"components.tools: {components.get('tools')}")
    lines.append(f"components.flow: {components.get('flow')}")
    lines.append(f"components.ui: {components.get('ui')}")
    lines.append(f"components.errors: {components.get('errors')}")

    changes = pack.get("changes") or {}
    if changes:
        lines.append(f"changes.files.count: {changes.get('files_changed_count')}")

    return "\n".join(lines)


def write_last_build(root: Path, pack: dict, plain_text: str, text: str) -> None:
    build_dir = root / ".namel3ss" / "build"
    build_dir.mkdir(parents=True, exist_ok=True)
    (build_dir / "last.json").write_text(_stable_json(pack), encoding="utf-8")
    (build_dir / "last.plain").write_text(plain_text.rstrip() + "\n", encoding="utf-8")
    (build_dir / "last.exists.txt").write_text(text.rstrip() + "\n", encoding="utf-8")


def _stable_json(payload: object) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


__all__ = ["build_plain_text", "stable_bullets", "stable_join", "stable_truncate", "write_last_build"]
