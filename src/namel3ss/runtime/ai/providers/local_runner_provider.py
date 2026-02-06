from __future__ import annotations

from namel3ss.runtime.ai.provider import AIProvider, AIResponse
from namel3ss.runtime.ai.providers.provider_pack_support import digest_for_call, ensure_mode_supported, input_mode, payload_seed


class LocalRunnerProvider(AIProvider):
    def ask(self, *, model: str, system_prompt: str | None, user_input: str, tools=None, memory=None, tool_results=None):
        mode = input_mode(user_input)
        ensure_mode_supported(provider="local_runner", mode=mode, allowed=("text",))
        seed = payload_seed(user_input)
        digest = digest_for_call(
            provider="local_runner",
            model=model,
            system_prompt=system_prompt,
            user_input=user_input,
            seed=seed,
        )
        model_name = model.split(":", 1)[-1]
        text = f"local_runner:{model_name} deterministic_output:{digest[:24]}"
        return AIResponse(output=text)


__all__ = ["LocalRunnerProvider"]
