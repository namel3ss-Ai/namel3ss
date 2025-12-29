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


def normalize_lines(lines: list[str], *, limit: int = 8) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for line in lines:
        text = stable_truncate(str(line).strip())
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
        if len(result) >= limit:
            break
    return result


def build_plain_text(pack: dict) -> str:
    lines: list[str] = []
    lines.append(f"summary: {pack.get('summary') or ''}")
    lines.append(f"api_version: {pack.get('api_version') or ''}")
    lines.append(f"flow.name: {pack.get('flow_name') or ''}")

    intent = pack.get("intent") or {}
    lines.append(f"intent.purpose: {intent.get('purpose') or ''}")
    if intent.get("requires"):
        lines.append(f"intent.requires: {intent.get('requires')}")
    lines.append(f"intent.audited: {intent.get('audited')}")
    expected = intent.get("expected_effects") or []
    if expected:
        lines.append(f"intent.expected_effects: {stable_join([str(item) for item in expected])}")

    outcome = pack.get("outcome") or {}
    lines.append(f"outcome.status: {outcome.get('status')}")
    lines.append(f"outcome.returned: {outcome.get('returned')}")
    if outcome.get("return_summary") is not None:
        lines.append(f"outcome.return_summary: {outcome.get('return_summary')}")

    tools = outcome.get("tool_summary") or {}
    lines.append(f"outcome.tools.ok: {tools.get('ok')}")
    lines.append(f"outcome.tools.blocked: {tools.get('blocked')}")
    lines.append(f"outcome.tools.error: {tools.get('error')}")

    memory = outcome.get("memory_summary") or {}
    if memory:
        lines.append(f"outcome.memory.written: {memory.get('written')}")

    skipped = outcome.get("skipped_summary") or {}
    if skipped:
        lines.append(f"outcome.skipped.total: {skipped.get('total')}")
        lines.append(f"outcome.skipped.branches: {skipped.get('branches')}")
        lines.append(f"outcome.skipped.cases: {skipped.get('cases')}")
        lines.append(f"outcome.skipped.tools_blocked: {skipped.get('tools_blocked')}")

    reasons = pack.get("reasons") or []
    lines.append(f"reasons.count: {len(reasons)}")
    for idx, reason in enumerate(reasons, start=1):
        lines.append(f"reason.{idx}: {reason}")

    what_not = pack.get("what_not") or []
    lines.append(f"what_not.count: {len(what_not)}")
    for idx, item in enumerate(what_not, start=1):
        lines.append(f"what_not.{idx}: {item}")

    return "\n".join(lines)


def write_last_flow(root: Path, pack: dict, plain_text: str, text: str) -> None:
    flow_dir = root / ".namel3ss" / "flow"
    flow_dir.mkdir(parents=True, exist_ok=True)
    (flow_dir / "last.json").write_text(_stable_json(pack), encoding="utf-8")
    (flow_dir / "last.plain").write_text(plain_text.rstrip() + "\n", encoding="utf-8")
    (flow_dir / "last.what.txt").write_text(text.rstrip() + "\n", encoding="utf-8")


def _stable_json(payload: object) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


__all__ = [
    "build_plain_text",
    "normalize_lines",
    "stable_bullets",
    "stable_join",
    "stable_truncate",
    "write_last_flow",
]
