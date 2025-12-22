from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AITrace:
    ai_name: str
    agent_name: Optional[str]
    ai_profile_name: Optional[str]
    model: str
    system_prompt: Optional[str]
    input: str
    output: str
    memory: dict
    tool_calls: list
    tool_results: list
    canonical_events: list[dict] = field(default_factory=list)
