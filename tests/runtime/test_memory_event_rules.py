from namel3ss.runtime.memory.events import (
    EVENT_CONTEXT,
    EVENT_CORRECTION,
    EVENT_DECISION,
    EVENT_EXECUTION,
    EVENT_FACT,
    EVENT_PREFERENCE,
    classify_event_type,
)
from namel3ss.runtime.memory.facts import extract_fact


def test_event_classification_rules():
    assert classify_event_type("I prefer concise summaries.") == EVENT_PREFERENCE
    assert classify_event_type("We decided to use weekly releases.") == EVENT_DECISION
    assert classify_event_type("My name is Ada.") == EVENT_FACT
    assert classify_event_type("Actually, my name is Ada.") == EVENT_CORRECTION
    assert classify_event_type("All good!") == EVENT_CONTEXT
    assert classify_event_type("", has_tool_events=True) == EVENT_EXECUTION


def test_fact_extraction_allowlist_and_safety():
    fact = extract_fact("My name is Ada Lovelace.")
    assert fact is not None
    assert fact.key == "name"
    assert fact.value == "Ada Lovelace"
    assert extract_fact("My email is ada@example.com") is None
