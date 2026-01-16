from __future__ import annotations

from pathlib import Path

import pytest

from namel3ss.cli.app_loader import load_program
from namel3ss.runtime.run_pipeline import build_flow_payload, finalize_run_payload
from namel3ss.runtime.store.memory_store import MemoryStore
from namel3ss.traces.schema import TraceEventType


def _run_payload(tmp_path: Path, source: str, *, flow_name: str = "demo", state: dict | None = None) -> dict:
    app_path = tmp_path / "app.ai"
    app_path.write_text(source, encoding="utf-8")
    program, _ = load_program(app_path.as_posix())
    outcome = build_flow_payload(
        program,
        flow_name,
        state=state or {},
        input={},
        store=MemoryStore(),
        project_root=tmp_path,
    )
    return finalize_run_payload(outcome.payload, secret_values=[])


def _trace_event(payload: dict, event_type: str) -> dict | None:
    traces = payload.get("traces") if isinstance(payload, dict) else None
    if not isinstance(traces, list):
        return None
    for trace in traces:
        if isinstance(trace, dict) and trace.get("type") == event_type:
            return trace
    return None


def test_missing_requires_blocks_mutation(tmp_path: Path) -> None:
    source = '''spec is "1.0"

record "Item":
  name text

flow "seed":
  save Item
'''.lstrip()
    payload = _run_payload(tmp_path, source, flow_name="seed", state={"item": {"name": "Alpha"}})
    blocked = _trace_event(payload, TraceEventType.MUTATION_BLOCKED)
    assert payload.get("ok") is False
    assert blocked is not None
    assert blocked.get("reason_code") == "policy_missing"


def test_audit_required_blocks_unaudited_mutation(tmp_path: Path, monkeypatch) -> None:
    source = '''spec is "1.0"

record "Item":
  name text

flow "seed": requires true
  save Item
'''.lstrip()
    monkeypatch.setenv("N3_AUDIT_REQUIRED", "1")
    payload = _run_payload(tmp_path, source, flow_name="seed", state={"item": {"name": "Alpha"}})
    blocked = _trace_event(payload, TraceEventType.MUTATION_BLOCKED)
    assert payload.get("ok") is False
    assert blocked is not None
    assert blocked.get("reason_code") == "audit_required"


def test_mutation_action_rule_evaluates_at_write(tmp_path: Path) -> None:
    source = '''spec is "1.0"

record "Item":
  name text

flow "remove": requires mutation.action is "delete"
  delete "Item" where name is "Alpha"
'''.lstrip()
    payload = _run_payload(tmp_path, source, flow_name="remove")
    allowed = _trace_event(payload, TraceEventType.MUTATION_ALLOWED)
    assert payload.get("ok") is True
    assert allowed is not None
    assert allowed.get("action") == "delete"


def test_mutation_action_mismatch_blocks(tmp_path: Path) -> None:
    source = '''spec is "1.0"

record "Item":
  name text

flow "remove": requires mutation.action is "create"
  delete "Item" where name is "Alpha"
'''.lstrip()
    payload = _run_payload(tmp_path, source, flow_name="remove")
    blocked = _trace_event(payload, TraceEventType.MUTATION_BLOCKED)
    assert payload.get("ok") is False
    assert blocked is not None
    assert blocked.get("reason_code") == "access_denied"
