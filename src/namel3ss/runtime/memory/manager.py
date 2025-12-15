from __future__ import annotations

from typing import Dict, List, Optional

from namel3ss.ir import nodes as ir
from namel3ss.runtime.memory.profile import ProfileMemory
from namel3ss.runtime.memory.semantic import SemanticMemory
from namel3ss.runtime.memory.short_term import ShortTermMemory


class MemoryManager:
    def __init__(self) -> None:
        self.short_term = ShortTermMemory()
        self.profile = ProfileMemory()
        self.semantic = SemanticMemory()

    def _session(self, state: Dict[str, object]) -> str:
        if isinstance(state.get("user"), dict) and "id" in state["user"]:
            return str(state["user"]["id"])
        return "anonymous"

    def recall_context(self, ai: ir.AIDecl, user_input: str, state: Dict[str, object]) -> dict:
        session = self._session(state)
        memory = ai.memory
        context = {"short_term": [], "semantic": [], "profile": []}
        if memory.short_term > 0:
            context["short_term"] = self.short_term.recall(session, memory.short_term)
        if memory.semantic:
            context["semantic"] = self.semantic.recall(session, user_input, top_k=3)
        if memory.profile:
            context["profile"] = self.profile.recall(session)
        return context

    def record_interaction(
        self,
        ai: ir.AIDecl,
        state: Dict[str, object],
        user_input: str,
        ai_output: str,
        tool_events: List[dict],
    ) -> None:
        session = self._session(state)
        message = {"role": "user", "content": user_input}
        self.short_term.record(session, message)
        ai_message = {"role": "ai", "content": ai_output}
        self.short_term.record(session, ai_message)
        if ai.memory.semantic:
            snippet = f"user:{user_input} ai:{ai_output}"
            if tool_events:
                snippet += f" tools:{tool_events}"
            self.semantic.record(session, snippet)

