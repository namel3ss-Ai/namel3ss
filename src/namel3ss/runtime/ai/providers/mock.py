from __future__ import annotations

from namel3ss.runtime.ai.provider import AIProvider, AIResponse, AIToolCallResponse


class MockProvider(AIProvider):
    def __init__(self, tool_call_sequence=None):
        self.tool_call_sequence = tool_call_sequence or []
        self.call_index = 0

    def ask(self, *, model: str, system_prompt: str | None, user_input: str, tools=None, memory=None, tool_results=None):
        if self.call_index < len(self.tool_call_sequence):
            resp = self.tool_call_sequence[self.call_index]
            self.call_index += 1
            if isinstance(resp, AIToolCallResponse):
                return resp
        prefix = f"[{model}]"
        mem_note = ""
        if memory:
            mem_note = f" | mem:st={len(memory.get('short_term', []))}"
        if system_prompt:
            return AIResponse(output=str(f"{prefix} {system_prompt} :: {user_input}{mem_note}"))
        return AIResponse(output=str(f"{prefix} {user_input}{mem_note}"))
