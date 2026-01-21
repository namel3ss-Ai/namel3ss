from __future__ import annotations

from pathlib import Path

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.executor import Executor
from namel3ss.runtime.store.memory_store import MemoryStore
from tests.conftest import lower_ir_program


def _build_executor(tmp_path: Path, source: str) -> Executor:
    program = lower_ir_program(source)
    flow = program.flows[0]
    return Executor(
        flow,
        schemas={},
        store=MemoryStore(),
        jobs={job.name: job for job in program.jobs},
        job_order=[job.name for job in program.jobs],
        capabilities=program.capabilities,
        project_root=str(tmp_path),
        app_path=(tmp_path / "app.ai").as_posix(),
    )


def test_scheduled_jobs_follow_enqueue_order(tmp_path: Path) -> None:
    source = '''spec is "1.0"

capabilities:
  jobs
  scheduling

job "beta":
  return "beta"

job "alpha":
  return "alpha"

job "gamma":
  return "gamma"

flow "demo":
  enqueue job "beta" after 1
  enqueue job "alpha" after 1
  enqueue job "gamma" after 1
  tick 1
  return "ok"
'''
    executor = _build_executor(tmp_path, source)
    result = executor.run()

    started = [event["job"] for event in result.traces if event.get("type") == "job_started"]
    assert started == ["beta", "alpha", "gamma"]

    scheduled = [event for event in result.traces if event.get("type") == "job_scheduled"]
    assert scheduled
    assert all(event.get("due_time") == 1 for event in scheduled)

    time_events = [event for event in result.traces if event.get("type") == "logical_time_advanced"]
    assert time_events
    assert time_events[0]["from"] == 0
    assert time_events[0]["to"] == 1


def test_tick_requires_scheduling_capability(tmp_path: Path) -> None:
    source = '''spec is "1.0"

capabilities:
  jobs

job "demo":
  return "ok"

flow "demo":
  tick 1
  return "done"
'''
    executor = _build_executor(tmp_path, source)
    with pytest.raises(Namel3ssError, match="Scheduling capability is not enabled"):
        executor.run()


def test_scheduled_enqueue_requires_scheduling_capability(tmp_path: Path) -> None:
    source = '''spec is "1.0"

capabilities:
  jobs

job "demo":
  return "ok"

flow "demo":
  enqueue job "demo" after 1
  return "done"
'''
    executor = _build_executor(tmp_path, source)
    with pytest.raises(Namel3ssError, match="Scheduling capability is not enabled"):
        executor.run()
