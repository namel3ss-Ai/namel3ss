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


def test_performance_scalability_capability_parses() -> None:
    source = '''spec is "1.0"

capabilities:
  performance_scalability

flow "demo":
  return "ok"
'''
    program = parse(source)
    assert "performance_scalability" in program.capabilities


def test_decoupled_ui_api_capability_parses() -> None:
    source = '''spec is "1.0"

capabilities:
  decoupled_ui_api

flow "demo":
  return "ok"
'''
    program = parse(source)
    assert "decoupled_ui_api" in program.capabilities


def test_ecosystem_developer_experience_capability_parses() -> None:
    source = '''spec is "1.0"

capabilities:
  ecosystem_developer_experience

flow "demo":
  return "ok"
'''
    program = parse(source)
    assert "ecosystem_developer_experience" in program.capabilities


def test_versioning_quality_mlops_capability_parses() -> None:
    source = '''spec is "1.0"

capabilities:
  versioning_quality_mlops

flow "demo":
  return "ok"
'''
    program = parse(source)
    assert "versioning_quality_mlops" in program.capabilities


def test_security_compliance_capability_parses() -> None:
    source = '''spec is "1.0"

capabilities:
  security_compliance

flow "demo":
  return "ok"
'''
    program = parse(source)
    assert "security_compliance" in program.capabilities


def test_vision_and_speech_capabilities_parse() -> None:
    source = '''spec is "1.0"

capabilities:
  vision
  speech

flow "demo":
  return "ok"
'''
    program = parse(source)
    assert "vision" in program.capabilities
    assert "speech" in program.capabilities


def test_training_capability_parses() -> None:
    source = '''spec is "1.0"

capabilities:
  training

flow "demo":
  return "ok"
'''
    program = parse(source)
    assert "training" in program.capabilities


def test_streaming_capability_parses() -> None:
    source = '''spec is "1.0"

capabilities:
  streaming

flow "demo":
  return "ok"
'''
    program = parse(source)
    assert "streaming" in program.capabilities


def test_performance_capability_parses() -> None:
    source = '''spec is "1.0"

capabilities:
  performance

flow "demo":
  return "ok"
'''
    program = parse(source)
    assert "performance" in program.capabilities


def test_dependency_management_capability_parses() -> None:
    source = '''spec is "1.0"

capabilities:
  dependency_management

flow "demo":
  return "ok"
'''
    program = parse(source)
    assert "dependency_management" in program.capabilities
