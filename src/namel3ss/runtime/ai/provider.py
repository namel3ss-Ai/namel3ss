from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class AIResponse:
    output: str


class AIProvider:
    def ask(
        self,
        *,
        model: str,
        system_prompt: Optional[str],
        user_input: str,
        tools: Optional[List[Dict[str, object]]] = None,
        memory: Optional[Dict[str, object]] = None,
        tool_results: Optional[List[Dict[str, object]]] = None,
    ) -> AIResponse:
        raise NotImplementedError


@dataclass
class AIToolCallResponse:
    tool_name: str
    args: Dict[str, object]
