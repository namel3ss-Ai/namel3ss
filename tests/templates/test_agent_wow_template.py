from __future__ import annotations

import os
import shutil
from pathlib import Path

from namel3ss.cli.app_loader import load_program
from namel3ss.cli.main import main as cli_main
from namel3ss.config.loader import load_config
from namel3ss.determinism import canonicalize_run_payload
from namel3ss.runtime.memory.api import MemoryManager
from namel3ss.runtime.run_pipeline import build_flow_payload, finalize_run_payload
from namel3ss.runtime.store.memory_store import MemoryStore
from namel3ss.secrets import collect_secret_values


def _run(args: list[str], cwd: Path) -> int:
    prev = os.getcwd()
    os.chdir(cwd)
    try:
        return cli_main(args)
    finally:
        os.chdir(prev)


def _scaffold(tmp_path: Path) -> Path:
    rc = _run(["new", "agent-wow", "demo"], tmp_path)
    assert rc == 0
    return tmp_path / "demo"


def _seed_brief(program, store: MemoryStore) -> None:
    schema = next(schema for schema in program.records if schema.name.endswith(".ProjectBrief"))
    store.save(schema, {"description": "Launch a premium onboarding concierge."})


def _reset_memory(app_dir: Path) -> None:
    memory_dir = app_dir / ".namel3ss" / "memory"
    if memory_dir.exists():
        shutil.rmtree(memory_dir)


def _run_flow(app_dir: Path, flow_name: str) -> dict:
    app_path = app_dir / "app.ai"
    program, _ = load_program(str(app_path))
    store = MemoryStore()
    _seed_brief(program, store)
    config = load_config(app_path=app_path)
    memory_manager = MemoryManager(project_root=str(app_dir), app_path=str(app_path))
    outcome = build_flow_payload(
        program,
        flow_name,
        store=store,
        memory_manager=memory_manager,
        config=config,
    )
    payload = finalize_run_payload(outcome.payload, collect_secret_values(config))
    return canonicalize_run_payload(payload)


def test_agent_wow_required_flows_exist(tmp_path: Path) -> None:
    app_dir = _scaffold(tmp_path)
    app_path = app_dir / "app.ai"
    program, _ = load_program(str(app_path))
    flow_names = {flow.name for flow in program.flows}
    for name in [
        "agent_wow.generate_plan",
        "agent_wow.run_parallel_feedback",
        "agent_wow.refine_plan",
        "agent_wow.remember_preference",
        "agent_wow.create_handoff",
        "agent_wow.apply_handoff",
        "agent_wow.follow_up",
        "agent_wow.reset_state",
    ]:
        assert name in flow_names


def test_agent_wow_parallel_run_is_deterministic(tmp_path: Path) -> None:
    app_dir = _scaffold(tmp_path)
    first = _run_flow(app_dir, "agent_wow.run_parallel_feedback")
    _reset_memory(app_dir)
    second = _run_flow(app_dir, "agent_wow.run_parallel_feedback")
    assert first == second
