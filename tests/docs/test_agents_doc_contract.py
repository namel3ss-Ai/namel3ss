from __future__ import annotations

from pathlib import Path


def test_agent_team_docs_and_memory_facts() -> None:
    root = Path(__file__).resolve().parents[2]
    learning = (root / "docs" / "learning-namel3ss.md").read_text(encoding="utf-8")
    assert "team of agents" in learning
    assert 'role is "Plans"' in learning
    assert "Agent ids are stable slugs" in learning

    memory = (root / "docs" / "memory.md").read_text(encoding="utf-8")
    assert "memory facts summary" in memory
    assert "last_updated_step" in memory

    studio = (root / "docs" / "studio.md").read_text(encoding="utf-8")
    assert "Agent team intent" in studio
    assert "last_updated_step" in studio

    trace = (root / "docs" / "trace-schema.md").read_text(encoding="utf-8")
    assert "agent_step_start" in trace
    assert "agent_step_end" in trace
    assert "merge_applied" in trace
