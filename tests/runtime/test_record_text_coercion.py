from tests.conftest import run_flow


SOURCE = '''record "Answer":
  field "text" is text

spec is "1.0"

flow "demo": requires true
  set state.answer.text is input.values.payload
  create "Answer" with state.answer as answer
  return answer
'''


def test_text_field_coerces_object_and_traces_warning():
    result = run_flow(SOURCE, input_data={"values": {"payload": {"output": "hello"}}})
    assert result.last_value["text"] == "hello"
    warnings = [
        trace for trace in result.traces if isinstance(trace, dict) and trace.get("type") == "type_mismatch_coerced"
    ]
    assert warnings
    warning = warnings[0]
    assert warning["record"] == "Answer"
    assert warning["field"] == "text"
    assert warning["expected"] == "text"
    assert warning["actual"] == "map"
