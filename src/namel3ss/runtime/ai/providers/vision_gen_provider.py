from __future__ import annotations

from namel3ss.runtime.ai.provider import AIProvider, AIResponse
from namel3ss.runtime.ai.providers.provider_pack_support import digest_for_call, ensure_mode_supported, input_mode, payload_seed


class VisionGenerationProvider(AIProvider):
    def ask(self, *, model: str, system_prompt: str | None, user_input: str, tools=None, memory=None, tool_results=None):
        mode = input_mode(user_input)
        ensure_mode_supported(provider="vision_gen", mode=mode, allowed=("image",))
        seed = payload_seed(user_input)
        digest = digest_for_call(
            provider="vision_gen",
            model=model,
            system_prompt=system_prompt,
            user_input=user_input,
            seed=seed,
        )
        image_id = digest[:16]
        image_url = f"vision-gen://images/{image_id}.png"
        prompt = (system_prompt or "").strip() or "generated image"
        description = f"{prompt} (seed={seed if seed is not None else int(digest[:8], 16)})"
        return AIResponse(
            output=description,
            image_id=image_id,
            image_url=image_url,
            description=description,
        )


__all__ = ["VisionGenerationProvider"]
