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
    input_structured: object | None = None
    input_format: Optional[str] = None
    canonical_events: list[dict] = field(default_factory=list)
    agent_id: Optional[str] = None
    role: Optional[str] = None
