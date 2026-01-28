from __future__ import annotations

from namel3ss.determinism import canonical_json_dumps

from .normalize import stable_bullets, stable_truncate


def render_audit(report: dict) -> str:
    lines: list[str] = []
    lines.append("Audit report")
    lines.append("")
    lines.append("Inputs")
    lines.extend(stable_bullets(_render_inputs(report.get("inputs"))))
    lines.append("")
    lines.append("Decisions")
    lines.extend(_render_decisions(report.get("decisions")))
    lines.append("")
    lines.append("Policies")
    lines.extend(stable_bullets(_render_policies(report.get("policies"))))
    lines.append("")
    lines.append("Outcomes")
    lines.extend(stable_bullets(_render_outcomes(report.get("outcomes"))))
    return "\n".join(lines).rstrip()


def _render_inputs(inputs: object) -> list[str]:
    if not isinstance(inputs, dict):
        return ["No inputs were recorded."]
    lines: list[str] = []
    for key in sorted(inputs.keys(), key=lambda item: str(item)):
        lines.append(f"{key}: {_format_value(inputs.get(key))}")
    return lines or ["No inputs were recorded."]


def _render_decisions(decisions: object) -> list[str]:
    if not isinstance(decisions, list) or not decisions:
        return stable_bullets(["No decisions were recorded."])
    lines: list[str] = []
    for idx, entry in enumerate(decisions, start=1):
        if not isinstance(entry, dict):
            continue
        prefix = f"{idx}. {entry.get('id')}"
        lines.append(prefix)
        lines.extend(stable_bullets(_decision_lines(entry)))
    return lines


def _decision_lines(entry: dict) -> list[str]:
    lines: list[str] = []
    category = entry.get("category")
    if category:
        lines.append(f"category: {category}")
    subject = entry.get("subject")
    if subject is not None:
        lines.append(f"subject: {stable_truncate(str(subject))}")
    inputs = entry.get("inputs")
    lines.append(f"inputs: {_format_value(inputs)}")
    rules = entry.get("rules")
    lines.append(f"rules: {_format_value(rules)}")
    outcome = entry.get("outcome")
    lines.append(f"outcome: {_format_value(outcome)}")
    return lines


def _render_policies(policies: object) -> list[str]:
    if not policies:
        return ["No policies were recorded."]
    return [f"policy: {_format_value(policies)}"]


def _render_outcomes(outcomes: object) -> list[str]:
    if not outcomes:
        return ["No outcomes were recorded."]
    return [f"summary: {_format_value(outcomes)}"]


def _format_value(value: object) -> str:
    if isinstance(value, (dict, list)):
        return canonical_json_dumps(value, pretty=False, drop_run_keys=False)
    if value is None:
        return ""
    return stable_truncate(str(value))


__all__ = ["render_audit"]
