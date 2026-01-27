from __future__ import annotations

from tests.conftest import lower_ir_program


def test_policy_block_lowers_to_ir() -> None:
    source = '''
policy
  deny ingestion.review
  require retrieval.include_warn with retrieval.include_warn
'''.lstrip()
    program = lower_ir_program(source)
    policy = program.policy
    assert policy is not None
    rules = {rule.action: rule for rule in policy.rules}
    assert rules["ingestion.review"].mode == "deny"
    assert rules["retrieval.include_warn"].permissions == ("retrieval.include_warn",)
