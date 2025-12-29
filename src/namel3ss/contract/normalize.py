from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from namel3ss.ir.model.program import Program


def stable_join(items: list[str], sep: str = ", ") -> str:
    return sep.join(items)


def stable_bullets(lines: list[str]) -> list[str]:
    return [line if line.startswith("- ") else f"- {line}" for line in lines]


def stable_truncate(text: str, limit: int = 120) -> str:
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def derive_flow_names(program: Program) -> tuple[str, ...]:
    return tuple(sorted({flow.name for flow in program.flows}))


def derive_features_used(program: Program) -> tuple[str, ...]:
    features: set[str] = set()
    if program.ais:
        features.add("ai")
    if program.tools:
        features.add("tools")
    if _memory_used(program):
        features.add("memory")
    if program.pages:
        features.add("pages")
    if program.records:
        features.add("records")
    if program.agents:
        features.add("agents")
    if program.identity is not None:
        features.add("identity")
    if _theme_used(program):
        features.add("theme")
    return tuple(sorted(features))


def derive_capabilities_required(program: Program) -> tuple[str, ...]:
    caps: set[str] = set()
    if program.ais:
        caps.add("ai")
    if program.tools:
        caps.add("tools")
    if program.identity is not None:
        caps.add("identity")
    if _memory_used(program):
        caps.add("memory")
    return tuple(sorted(caps))


def build_plain_text(pack: dict[str, object]) -> str:
    lines: list[str] = []
    lines.append(f"spec_version: {pack.get('spec_version') or ''}")
    lines.append(f"source_hash: {pack.get('source_hash') or ''}")

    summary = pack.get("program_summary") or {}
    if isinstance(summary, dict):
        _append_summary(lines, summary, "flows")
        _append_summary(lines, summary, "records")
        _append_summary(lines, summary, "pages")
        _append_summary(lines, summary, "ais")
        _append_summary(lines, summary, "tools")
        _append_summary(lines, summary, "agents")
        identity = summary.get("identity") or {}
        if isinstance(identity, dict):
            lines.append(f"identity.present: {identity.get('present')}")
            lines.append(f"identity.name: {identity.get('name') or ''}")

    _append_list(lines, "features", pack.get("features_used"))
    _append_list(lines, "capabilities", pack.get("capabilities_required"))
    _append_list(lines, "warnings", pack.get("warnings"))

    return "\n".join(lines)


def write_contract_artifacts(root: Path, pack: dict[str, object], plain_text: str, text: str) -> None:
    contract_dir = root / ".namel3ss" / "contract"
    contract_dir.mkdir(parents=True, exist_ok=True)
    (contract_dir / "last.json").write_text(_stable_json(pack), encoding="utf-8")
    (contract_dir / "last.plain").write_text(plain_text.rstrip() + "\n", encoding="utf-8")
    (contract_dir / "last.exists.txt").write_text(text.rstrip() + "\n", encoding="utf-8")

    source_hash = pack.get("source_hash")
    if isinstance(source_hash, str) and source_hash:
        history_dir = contract_dir / "history"
        history_dir.mkdir(parents=True, exist_ok=True)
        (history_dir / f"{source_hash}.json").write_text(_stable_json(pack), encoding="utf-8")


def _append_summary(lines: list[str], summary: dict[str, object], key: str) -> None:
    entry = summary.get(key) or {}
    if not isinstance(entry, dict):
        return
    count = entry.get("count")
    names = entry.get("names") or []
    lines.append(f"{key}.count: {count}")
    if isinstance(names, list) and names:
        lines.append(f"{key}.names: {stable_join([str(name) for name in names])}")
    else:
        lines.append(f"{key}.names: ")


def _append_list(lines: list[str], label: str, values: Iterable[str] | None) -> None:
    items = list(values or [])
    lines.append(f"{label}.count: {len(items)}")
    for idx, item in enumerate(items, start=1):
        lines.append(f"{label}.{idx}: {item}")


def _memory_used(program: Program) -> bool:
    for ai in program.ais.values():
        memory = ai.memory
        if memory.short_term or memory.semantic or memory.profile:
            return True
    return False


def _theme_used(program: Program) -> bool:
    if program.theme and program.theme != "system":
        return True
    if program.theme_tokens:
        return True
    if getattr(program, "theme_runtime_supported", False):
        return True
    preference = getattr(program, "theme_preference", {}) or {}
    if preference.get("allow_override", False):
        return True
    if preference.get("persist", "none") != "none":
        return True
    return False


def _stable_json(payload: object) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


__all__ = [
    "build_plain_text",
    "derive_capabilities_required",
    "derive_features_used",
    "derive_flow_names",
    "stable_bullets",
    "stable_join",
    "stable_truncate",
    "write_contract_artifacts",
]
