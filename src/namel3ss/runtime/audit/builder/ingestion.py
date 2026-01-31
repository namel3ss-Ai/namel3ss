from __future__ import annotations

from namel3ss.traces.schema import TraceEventType

from ..model import DecisionStep
from .utils import string_list, trace_events


def ingestion_decisions(state: dict, upload_id: str | None) -> list[DecisionStep]:
    ingestion = state.get("ingestion")
    if not isinstance(ingestion, dict):
        return []
    steps: list[DecisionStep] = []
    for uid in sorted(ingestion.keys(), key=lambda item: str(item)):
        report = ingestion.get(uid)
        if not isinstance(report, dict):
            continue
        uid_text = str(uid)
        if upload_id and uid_text != upload_id:
            continue
        gate = report.get("gate") if isinstance(report.get("gate"), dict) else None
        reasons = string_list(gate.get("reasons")) if gate else string_list(report.get("reasons"))
        rules = ["quality gate"] + reasons if reasons else ["quality gate"]
        inputs = {
            "upload_id": uid_text,
            "method_used": report.get("method_used"),
            "detected": report.get("detected"),
            "signals": report.get("signals"),
        }
        if gate:
            inputs["gate"] = gate
        outcome = {"status": report.get("status")}
        if gate and isinstance(gate.get("status"), str):  # allowed | blocked
            outcome["gate"] = gate.get("status")
        steps.append(
            DecisionStep(
                id=f"ingestion:{uid_text}",
                category="ingestion",
                subject=uid_text,
                inputs=inputs,
                rules=rules,
                outcome=outcome,
            )
        )
    return steps


def review_decisions(state: dict, traces: list[dict], upload_id: str | None) -> list[DecisionStep]:
    steps: list[DecisionStep] = []
    review_events = trace_events(traces, TraceEventType.INGESTION_REVIEWED)
    for idx, event in enumerate(review_events, start=1):
        steps.append(
            DecisionStep(
                id=f"review:ingestion_review:{idx}",
                category="review",
                subject=None,
                inputs={},
                rules=["review requested"],
                outcome={"status": "run", "count": event.get("count")},
            )
        )
    seen_skips: set[str] = set()
    skip_events = trace_events(traces, TraceEventType.INGESTION_SKIPPED)
    for event in skip_events:
        uid = event.get("upload_id")
        if not isinstance(uid, str) or not uid:
            continue
        if upload_id and uid != upload_id:
            continue
        seen_skips.add(uid)
        steps.append(
            DecisionStep(
                id=f"review:ingestion_skip:{uid}",
                category="review",
                subject=uid,
                inputs={"upload_id": uid},
                rules=string_list(event.get("reasons")),
                outcome={"status": "skipped", "quality": event.get("status")},
            )
        )
    replace_events = trace_events(traces, TraceEventType.UPLOAD_REPLACE_REQUESTED)
    for event in replace_events:
        uid = event.get("upload_id")
        if not isinstance(uid, str) or not uid:
            continue
        if upload_id and uid != upload_id:
            continue
        steps.append(
            DecisionStep(
                id=f"review:upload_replace:{uid}",
                category="review",
                subject=uid,
                inputs={"upload_id": uid},
                rules=["replacement requested"],
                outcome={"status": "requested"},
            )
        )
    steps.extend(_inferred_skip_decisions(state, seen_skips, upload_id))
    return steps


def _inferred_skip_decisions(state: dict, seen_skips: set[str], upload_id: str | None) -> list[DecisionStep]:
    ingestion = state.get("ingestion")
    if not isinstance(ingestion, dict):
        return []
    steps: list[DecisionStep] = []
    for uid, report in ingestion.items():
        if not isinstance(report, dict):
            continue
        uid_text = str(uid)
        if upload_id and uid_text != upload_id:
            continue
        if uid_text in seen_skips:
            continue
        method_used = report.get("method_used")
        reasons = string_list(report.get("reasons"))
        if method_used != "skip" and "skipped" not in reasons:
            continue
        steps.append(
            DecisionStep(
                id=f"review:ingestion_skip:{uid_text}",
                category="review",
                subject=uid_text,
                inputs={"upload_id": uid_text},
                rules=reasons or ["skipped"],
                outcome={"status": "skipped", "quality": report.get("status")},
            )
        )
    return steps


__all__ = ["ingestion_decisions", "review_decisions"]
