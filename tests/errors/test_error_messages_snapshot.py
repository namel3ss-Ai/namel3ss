from __future__ import annotations

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.render import format_error
from namel3ss.parser.core import parse
from namel3ss.runtime.executor.api import execute_program_flow
from namel3ss.runtime.store.memory_store import MemoryStore
from namel3ss.runtime.ui.actions import handle_action
from tests.conftest import lower_ir_program


def _normalize(text: str) -> str:
    return text.replace("\r\n", "\n").strip()


def test_unsupported_operator_error_snapshot() -> None:
    source = 'spec is "1.0"\n\nflow "demo":\n  return 1 ^ 2\n'
    with pytest.raises(Namel3ssError) as excinfo:
        parse(source)
    rendered = format_error(excinfo.value, source)
    expected = (
        "[line 4, col 12] What happened: Unsupported character '^' in namel3ss source.\n"
        "Why: Only supported operators are +, -, *, / and comparison words like `is greater than`.\n"
        "Fix: Remove the character or rewrite using supported arithmetic/comparison syntax.\n"
        "Example: Use `total + 2.5` or `if price is greater than 10:`.\n"
        "  return 1 ^ 2\n"
        "           ^"
    )
    assert _normalize(rendered) == expected


def test_unknown_flow_message_snapshot() -> None:
    program = lower_ir_program('spec is "1.0"\n\nflow "demo":\n  return "ok"\n')
    with pytest.raises(Namel3ssError) as excinfo:
        execute_program_flow(program, "missing")
    expected = (
        "What happened: Unknown flow 'missing'.\n"
        "Why: The app defines flows: demo.\n"
        "Fix: Call an existing flow or add it to your app.ai file.\n"
        'Example: n3 app.ai flow "demo"'
    )
    assert _normalize(str(excinfo.value)) == expected


def test_unknown_action_message_snapshot() -> None:
    program = lower_ir_program(
        'record "User":\n'
        "  name string\n\n"
        'page "home":\n'
        '  form is "User"\n'
    )
    with pytest.raises(Namel3ssError) as excinfo:
        handle_action(program, action_id="missing", payload={}, store=MemoryStore())
    expected = (
        "What happened: Unknown action 'missing'.\n"
        "Why: The manifest exposes actions: page.home.form.user.\n"
        "Fix: Use an action id from `n3 app.ai actions` or define the action in app.ai.\n"
        "Example: n3 app.ai page.home.form.user {}"
    )
    assert _normalize(str(excinfo.value)) == expected


def test_submit_form_missing_values_snapshot() -> None:
    program = lower_ir_program(
        'record "User":\n'
        "  name string\n\n"
        'page "home":\n'
        '  form is "User"\n'
    )
    with pytest.raises(Namel3ssError) as excinfo:
        handle_action(program, action_id="page.home.form.user", payload={"values": "x"}, store=MemoryStore())
    expected = (
        "What happened: Submit form payload is missing a 'values' object.\n"
        "Why: Form submissions read values from the 'values' key; other top-level keys are ignored. Payload included reserved keys: values.\n"
        "Fix: Send {\"values\": {...}} or pass a flat object so it can be wrapped automatically.\n"
        'Example: {"values":{"email":"ada@example.com"}} (or {"email":"ada@example.com"})'
    )
    assert _normalize(str(excinfo.value)) == expected
