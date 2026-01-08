from __future__ import annotations

from namel3ss.determinism import canonical_trace_json
from namel3ss.runtime.ai.mock_provider import MockProvider
from namel3ss.runtime.executor import Executor
from tests.conftest import lower_ir_program


SOURCE_FIRST_VALID = '''ai "assistant":
  model is "gpt-4.1"

agent "alpha":
  ai is "assistant"
  system_prompt is "alpha"

agent "beta":
  ai is "assistant"
  system_prompt is "beta"

flow "demo":
  run agents in parallel:
    agent "alpha" with input: "task"
    agent "beta" with input: "task"
  merge:
    policy is "first_valid"
    require_keys is list:
      "text"
  as result
  return result
'''


SOURCE_RANKED = '''ai "assistant":
  model is "gpt-4.1"

agent "short":
  ai is "assistant"
  system_prompt is "short"

agent "long":
  ai is "assistant"
  system_prompt is "much longer prompt"

flow "demo":
  run agents in parallel:
    agent "short" with input: "task"
    agent "long" with input: "task"
  merge:
    policy is "ranked"
    score_rule is "text_length"
  as result
  return result
'''


SOURCE_CONSENSUS = '''ai "assistant":
  model is "gpt-4.1"

agent "a1":
  ai is "assistant"
  system_prompt is "shared"

agent "a2":
  ai is "assistant"
  system_prompt is "shared"

agent "a3":
  ai is "assistant"
  system_prompt is "other"

flow "demo":
  run agents in parallel:
    agent "a1" with input: "task"
    agent "a2" with input: "task"
    agent "a3" with input: "task"
  merge:
    policy is "consensus"
    min_consensus is 2
    consensus_key is "text"
  as result
  return result
'''


def _run(source: str):
    program = lower_ir_program(source)
    flow = program.flows[0]
    executor = Executor(flow, schemas={}, ai_profiles=program.ais, agents=program.agents, ai_provider=MockProvider())
    return executor.run()


def test_merge_first_valid_selects_first_candidate():
    result = _run(SOURCE_FIRST_VALID)
    output = result.last_value
    assert isinstance(output, dict)
    assert "alpha :: task" in output.get("text", "")


def test_merge_ranked_selects_longest_text():
    result = _run(SOURCE_RANKED)
    output = result.last_value
    assert isinstance(output, dict)
    assert "much longer prompt" in output.get("text", "")


def test_merge_consensus_selects_shared_output():
    result = _run(SOURCE_CONSENSUS)
    output = result.last_value
    assert isinstance(output, dict)
    assert "shared :: task" in output.get("text", "")


def test_merge_traces_are_deterministic():
    first = _run(SOURCE_RANKED)
    second = _run(SOURCE_RANKED)
    assert canonical_trace_json(first.traces) == canonical_trace_json(second.traces)
    assert first.last_value == second.last_value
