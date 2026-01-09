from __future__ import annotations

from dataclasses import fields, is_dataclass

from tests.conftest import parse_program


def _strip_positions(value):
    if isinstance(value, list):
        return [_strip_positions(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_strip_positions(item) for item in value)
    if is_dataclass(value):
        data = {}
        for field in fields(value):
            field_value = getattr(value, field.name)
            if field.name in {"line", "column"}:
                data[field.name] = None
            else:
                data[field.name] = _strip_positions(field_value)
        return type(value)(**data)
    return value


def test_access_sugar_lowers_to_list_map_ops() -> None:
    sugar = '''
flow "demo":
  let critic_text is feedback[0].text
'''
    core = '''
flow "demo":
  let critic_text is map get list get feedback at 0 key "text"
'''
    expr = parse_program(sugar).flows[0].body[0].expression
    expected = parse_program(core).flows[0].body[0].expression
    assert _strip_positions(expr) == _strip_positions(expected)


def test_agent_execution_sugar_lowers_to_parallel_run() -> None:
    sugar = '''
flow "demo":
  let goal is "Draft a checklist"
  plan with "planner"
  review in parallel with:
    "critic"
    "researcher"
  keep all feedback
  return "ok"
'''
    core = '''
flow "demo":
  let goal is "Draft a checklist"
  run agent "planner" with input: goal as plan
  run agents in parallel:
    agent "critic" with input: plan
    agent "researcher" with input: plan
  merge:
    policy is "all"
  as feedback
  return "ok"
'''
    sugar_body = parse_program(sugar).flows[0].body
    core_body = parse_program(core).flows[0].body
    assert _strip_positions(sugar_body) == _strip_positions(core_body)


def test_timeline_shows_sugar_lowers() -> None:
    sugar = '''
flow "demo":
  set state.run_id is "current"
  timeline shows:
    Start: "hello"
    Tools
  return "ok"
'''
    core = '''
flow "demo":
  set state.run_id is "current"
  set state.timeline_event with:
    run_id is state.run_id
    seq is 1
    stage is "Start"
    detail is "hello"
  create "TimelineEvent" with state.timeline_event as event
  set state.timeline_event with:
    run_id is state.run_id
    seq is 2
    stage is "Tools"
    detail is null
  create "TimelineEvent" with state.timeline_event as event
  return "ok"
'''
    sugar_body = parse_program(sugar).flows[0].body
    core_body = parse_program(core).flows[0].body
    assert _strip_positions(sugar_body) == _strip_positions(core_body)


def test_run_lifecycle_and_output_sugar_lowers() -> None:
    sugar = '''
flow "demo":
  let goal is "Ship the release"
  start a new run for goal using memory pack "agent-minimal"
  let mode is "single"
  let merge_policy is "none"
  let final_output is "ok"
  compute output hash
  record final output
  increment ai calls
  increment tool calls
  record policy violation
  return "done"
'''
    core = '''
flow "demo":
  let goal is "Ship the release"
  set state.run_id is "current"
  set state.ai_calls is 0
  set state.tool_calls is 0
  set state.policy_violations is 0
  set state.blocked_reason is "not run"
  delete "TimelineEvent" where run_id is state.run_id
  delete "AgentOutput" where run_id is state.run_id
  delete "RunResult" where run_id is state.run_id
  delete "ExplainNote" where run_id is state.run_id
  delete "SafetyStatus" where run_id is state.run_id
  delete "DebugMetric" where run_id is state.run_id
  set state.timeline_event with:
    run_id is state.run_id
    seq is 1
    stage is "Start"
    detail is goal
  create "TimelineEvent" with state.timeline_event as event
  set state.timeline_event with:
    run_id is state.run_id
    seq is 2
    stage is "Memory"
    detail is "pack: agent-minimal"
  create "TimelineEvent" with state.timeline_event as event
  let mode is "single"
  let merge_policy is "none"
  let final_output is "ok"
  let hash_result is hash text:
    value is final_output
  set state.result_record with:
    run_id is state.run_id
    mode is mode
    output is final_output
    output_hash is hash_result.hash
    merge_policy is merge_policy
    status is "ok"
  create "RunResult" with state.result_record as result
  set state.ai_calls is state.ai_calls + 1
  delete "DebugMetric" where run_id is state.run_id and label is "AI calls"
  set state.debug_metric with:
    run_id is state.run_id
    seq is 1
    label is "AI calls"
    value is state.ai_calls
  create "DebugMetric" with state.debug_metric as metric
  set state.tool_calls is state.tool_calls + 1
  delete "DebugMetric" where run_id is state.run_id and label is "Tool calls"
  set state.debug_metric with:
    run_id is state.run_id
    seq is 2
    label is "Tool calls"
    value is state.tool_calls
  create "DebugMetric" with state.debug_metric as metric
  set state.policy_violations is state.policy_violations + 1
  delete "DebugMetric" where run_id is state.run_id and label is "Policy violations"
  set state.debug_metric with:
    run_id is state.run_id
    seq is 3
    label is "Policy violations"
    value is state.policy_violations
  create "DebugMetric" with state.debug_metric as metric
  return "done"
'''
    sugar_body = parse_program(sugar).flows[0].body
    core_body = parse_program(core).flows[0].body
    assert _strip_positions(sugar_body) == _strip_positions(core_body)
