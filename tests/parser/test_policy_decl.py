from __future__ import annotations

import pytest

from namel3ss.errors.base import Namel3ssError
from tests.conftest import parse_program


def test_policy_block_parses_rules() -> None:
    source = '''
policy
  allow ingestion.run
  deny ingestion.skip
  require ingestion.review with ingestion.review, admin
'''.lstrip()
    program = parse_program(source)
    policy = program.policy
    assert policy is not None
    rules = {rule.action: rule for rule in policy.rules}
    assert rules["ingestion.run"].mode == "allow"
    assert rules["ingestion.skip"].mode == "deny"
    assert rules["ingestion.review"].mode == "require"
    assert rules["ingestion.review"].permissions == ["ingestion.review", "admin"]


def test_policy_require_needs_permissions() -> None:
    source = '''
policy
  require ingestion.review
'''.lstrip()
    with pytest.raises(Namel3ssError) as excinfo:
        parse_program(source)
    assert "Policy require is missing permissions." in excinfo.value.message


def test_policy_unknown_action_is_error() -> None:
    source = '''
policy
  allow ingestion.unknown
'''.lstrip()
    with pytest.raises(Namel3ssError) as excinfo:
        parse_program(source)
    assert "Unknown policy action" in excinfo.value.message
