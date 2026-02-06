from __future__ import annotations

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.explainability.seed_manager import normalize_seed, resolve_ai_call_seed


def test_resolve_ai_call_seed_is_deterministic_for_same_inputs() -> None:
    first = resolve_ai_call_seed(
        explicit_seed=None,
        global_seed=None,
        model="openai:gpt-4o-mini",
        user_input="hello world",
        context={"flow": "demo", "ai_profile": "assistant"},
    )
    second = resolve_ai_call_seed(
        explicit_seed=None,
        global_seed=None,
        model="openai:gpt-4o-mini",
        user_input="hello world",
        context={"flow": "demo", "ai_profile": "assistant"},
    )
    assert isinstance(first, int)
    assert first == second


def test_resolve_ai_call_seed_honors_explicit_seed() -> None:
    value = resolve_ai_call_seed(
        explicit_seed=99,
        global_seed=17,
        model="openai:gpt-4o-mini",
        user_input="hello world",
        context={"flow": "demo"},
    )
    assert value == 99


def test_resolve_ai_call_seed_uses_global_seed_when_present() -> None:
    value = resolve_ai_call_seed(
        explicit_seed=None,
        global_seed=41,
        model="openai:gpt-4o-mini",
        user_input="hello world",
        context={"flow": "demo"},
    )
    assert value == 41


def test_normalize_seed_rejects_boolean() -> None:
    with pytest.raises(Namel3ssError):
        normalize_seed(True)
