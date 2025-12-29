from __future__ import annotations

from .normalize import stable_bullets, stable_join, stable_truncate


def render_what(flow_pack: dict) -> str:
    intent = flow_pack.get("intent") or {}
    outcome = flow_pack.get("outcome") or {}
    flow_name = flow_pack.get("flow_name") or intent.get("flow_name") or "unknown"

    lines: list[str] = []
    lines.append("What the flow did")
    lines.append("")
    lines.append(f"Flow: {flow_name}")
    lines.append("")
    lines.append("Intent")
    lines.extend(stable_bullets(_intent_lines(intent)))
    lines.append("")
    lines.append("Outcome")
    lines.extend(stable_bullets(_outcome_lines(outcome)))
    lines.append("")
    lines.append("Why")
    lines.extend(stable_bullets(_reason_lines(flow_pack)))
    lines.append("")
    lines.append("What did not happen")
    lines.extend(stable_bullets(_what_not_lines(flow_pack)))
    return "\n".join(lines).rstrip()


def _intent_lines(intent: dict) -> list[str]:
    lines: list[str] = []
    purpose = intent.get("purpose") or ""
    if purpose:
        lines.append(_line(purpose))
    requires = intent.get("requires")
    if requires:
        lines.append(_line(f"requires: {requires}"))
    audited = "yes" if intent.get("audited") else "no"
    lines.append(_line(f"audited: {audited}"))
    expected = intent.get("expected_effects") or []
    if expected:
        lines.append(_line(f"expected effects: {stable_join([str(item) for item in expected])}"))
    return lines


def _outcome_lines(outcome: dict) -> list[str]:
    lines: list[str] = []
    status = outcome.get("status") or "unknown"
    lines.append(_line(f"status: {status}"))

    tool_summary = outcome.get("tool_summary") or {}
    if tool_summary:
        lines.append(
            _line(
                "tools: ok {ok}, blocked {blocked}, error {error}".format(
                    ok=tool_summary.get("ok", 0),
                    blocked=tool_summary.get("blocked", 0),
                    error=tool_summary.get("error", 0),
                )
            )
        )
    else:
        lines.append(_line("tools: none recorded"))

    memory_summary = outcome.get("memory_summary") or {}
    if memory_summary:
        lines.append(_line(f"memory: wrote {memory_summary.get('written', 0)} items"))

    if outcome.get("returned"):
        return_summary = outcome.get("return_summary")
        if return_summary:
            lines.append(_line(f"return: {return_summary}"))
        else:
            lines.append(_line("return: value"))
    return lines


def _reason_lines(flow_pack: dict) -> list[str]:
    reasons = flow_pack.get("reasons") or []
    if not reasons:
        return ["No reasons were recorded for this run."]
    return [_line(str(reason)) for reason in reasons]


def _what_not_lines(flow_pack: dict) -> list[str]:
    what_not = flow_pack.get("what_not") or []
    if not what_not:
        return ["None recorded."]
    return [_line(str(item)) for item in what_not]


def _line(text: str) -> str:
    text = text.strip()
    if not text:
        return text
    if text.endswith("."):
        return stable_truncate(text)
    return stable_truncate(f"{text}.")


__all__ = ["render_what"]
