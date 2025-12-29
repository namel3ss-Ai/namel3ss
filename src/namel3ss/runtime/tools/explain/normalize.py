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
    summary = pack.get("summary") or ""
    counts = pack.get("counts") or {}
    lines.append(f"summary: {summary}")
    lines.append(f"decisions.total: {counts.get('total')}")
    lines.append(f"decisions.ok: {counts.get('ok')}")
    lines.append(f"decisions.error: {counts.get('error')}")
    lines.append(f"decisions.blocked: {counts.get('blocked')}")
    decisions = pack.get("decisions") or []
    for idx, decision in enumerate(decisions, start=1):
        if not isinstance(decision, dict):
            continue
        prefix = f"tool.{idx}"
        lines.append(f"{prefix}.name: {decision.get('tool_name')}")
        lines.append(f"{prefix}.status: {decision.get('status')}")
        intent = decision.get("intent") or {}
        lines.append(f"{prefix}.intent: {intent.get('what')}")
        permission = decision.get("permission") or {}
        lines.append(f"{prefix}.allowed: {permission.get('allowed')}")
        reasons = permission.get("reasons") or []
        if reasons:
            lines.append(f"{prefix}.reasons: {stable_join([str(r) for r in reasons])}")
        effect = decision.get("effect") or {}
        if effect.get("duration_ms") is not None:
            lines.append(f"{prefix}.duration_ms: {effect.get('duration_ms')}")
    return "\n".join(lines)


def write_last_tools(root: Path, pack: dict, plain_text: str, text: str) -> None:
    tools_dir = root / ".namel3ss" / "tools"
    tools_dir.mkdir(parents=True, exist_ok=True)
    (tools_dir / "last.json").write_text(_stable_json(pack), encoding="utf-8")
    (tools_dir / "last.plain").write_text(plain_text.rstrip() + "\n", encoding="utf-8")
    (tools_dir / "last.with.txt").write_text(text.rstrip() + "\n", encoding="utf-8")


def _stable_json(payload: object) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


__all__ = ["build_plain_text", "stable_bullets", "stable_join", "stable_truncate", "write_last_tools"]
