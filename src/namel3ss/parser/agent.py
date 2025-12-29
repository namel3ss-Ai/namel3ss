from __future__ import annotations

"""Legacy shim for agent parsing."""

from namel3ss.parser.decl.agent import parse_agent_decl
from namel3ss.parser.stmt.run_agent import parse_run_agent_stmt, parse_run_agents_parallel

__all__ = ["parse_agent_decl", "parse_run_agent_stmt", "parse_run_agents_parallel"]
