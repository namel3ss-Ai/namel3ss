from namel3ss.lint.engine import lint_source


SOURCE_LIMIT = '''spec is "1.0"

ai "assistant":
  model is "mock"

agent "a1":
  ai is "assistant"
  system_prompt is "a1"

agent "a2":
  ai is "assistant"
  system_prompt is "a2"

agent "a3":
  ai is "assistant"
  system_prompt is "a3"

agent "a4":
  ai is "assistant"
  system_prompt is "a4"

flow "demo":
  run agents in parallel:
    agent "a1" with input: "task"
    agent "a2" with input: "task"
    agent "a3" with input: "task"
    agent "a4" with input: "task"
  as result
  return result
'''


SOURCE_CONSENSUS_UNREACHABLE = '''spec is "1.0"

ai "assistant":
  model is "mock"

agent "a1":
  ai is "assistant"
  system_prompt is "a1"

agent "a2":
  ai is "assistant"
  system_prompt is "a2"

flow "demo":
  run agents in parallel:
    agent "a1" with input: "task"
    agent "a2" with input: "task"
  merge:
    policy is "consensus"
    min_consensus is 3
  as result
  return result
'''


def test_parallel_agent_limit_is_linted():
    findings = lint_source(SOURCE_LIMIT)
    assert any(f.code == "agents.parallel_limit" for f in findings)


def test_consensus_unreachable_is_linted():
    findings = lint_source(SOURCE_CONSENSUS_UNREACHABLE)
    assert any(f.code == "agents.merge_consensus_unreachable" for f in findings)
