from namel3ss.runtime.ui.actions import handle_action
from namel3ss.traces.schema import TraceEventType
from tests.conftest import lower_ir_program


SOURCE = '''spec is "1.0"

ai "assistant":
  model is "gpt-4.1"

flow "demo":
  ask ai "assistant" with input: "Hello" as reply
  set state.reply is reply
  return reply

page "home":
  button "Ask":
    calls flow "demo"
'''


def test_canonical_ai_trace_events_present_and_grouped():
    program = lower_ir_program(SOURCE)
    response = handle_action(program, action_id="page.home.button.ask")
    trace = response["traces"][0]
    events = trace["canonical_events"]
    types = [event["type"] for event in events]
    assert types[0] == TraceEventType.MEMORY_RECALL
    assert TraceEventType.AI_CALL_STARTED in types
    assert TraceEventType.MEMORY_WRITE in types
    assert types.index(TraceEventType.AI_CALL_STARTED) > types.index(TraceEventType.MEMORY_RECALL)
    call_ids = {event["call_id"] for event in events if "call_id" in event}
    assert len(call_ids) == 1
    assert all(event["trace_version"] for event in events)
