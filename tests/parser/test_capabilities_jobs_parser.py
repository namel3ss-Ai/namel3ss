import pytest

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.parser.core import parse


def test_capabilities_block_parses() -> None:
    source = '''spec is "1.0"

capabilities:
  http
  jobs
  files

flow "demo":
  return "ok"
'''
    program = parse(source)
    assert program.capabilities == ["http", "jobs", "files"]


def test_capabilities_unknown_rejected() -> None:
    source = '''spec is "1.0"

capabilities:
  magic
'''
    with pytest.raises(Namel3ssError) as exc:
        parse(source)
    assert "Unknown capability" in exc.value.message


def test_job_decl_and_enqueue_parse() -> None:
    source = '''spec is "1.0"

capabilities:
  jobs

job "refresh" when state.ready is true:
  return "ok"

flow "demo":
  enqueue job "refresh" with input: map:
    "note" is "ok"
'''
    program = parse(source)
    assert len(program.jobs) == 1
    job = program.jobs[0]
    assert job.name == "refresh"
    assert job.when is not None

    flow = program.flows[0]
    stmt = flow.body[0]
    assert isinstance(stmt, ast.EnqueueJob)
    assert stmt.job_name == "refresh"
    assert stmt.input_expr is not None
