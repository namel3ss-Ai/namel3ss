from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.ai.provider import AIProvider, AIResponse
from namel3ss.runtime.ai.providers._shared.errors import require_env
from namel3ss.runtime.ai.providers.provider_pack_support import (
    deterministic_label,
    digest_for_call,
    ensure_mode_supported,
    input_mode,
    payload_seed,
)
from namel3ss.security import read_env


class HuggingFaceProvider(AIProvider):
    def ask(self, *, model: str, system_prompt: str | None, user_input: str, tools=None, memory=None, tool_results=None):
        _resolve_huggingface_key()
        mode = input_mode(user_input)
        ensure_mode_supported(provider="huggingface", mode=mode, allowed=("text", "image", "audio"))
        seed = payload_seed(user_input)
        digest = digest_for_call(
            provider="huggingface",
            model=model,
            system_prompt=system_prompt,
            user_input=user_input,
            seed=seed,
        )
        model_name = model.split(":", 1)[-1]

        if mode == "image":
            label = deterministic_label(digest, ("diagram", "receipt", "portrait", "landscape"))
            text = f"huggingface:{model_name} image label={label}"
            return AIResponse(output=text, description=text)

        if mode == "audio":
            transcript = f"huggingface:{model_name} transcript:{digest[:24]}"
            return AIResponse(output=transcript, transcript=transcript)

        text = f"huggingface:{model_name} response:{digest[:24]}"
        return AIResponse(output=text)


def _resolve_huggingface_key() -> str:
    preferred = read_env("NAMEL3SS_HUGGINGFACE_API_KEY")
    if preferred is not None and str(preferred).strip() != "":
        return require_env("huggingface", "NAMEL3SS_HUGGINGFACE_API_KEY", preferred)
    for alias in ("HUGGINGFACE_API_KEY", "HUGGINGFACEHUB_API_TOKEN"):
        value = read_env(alias)
        if value is not None and str(value).strip() != "":
            return require_env("huggingface", alias, value)
    raise Namel3ssError(
        "Missing HuggingFace API key. Set NAMEL3SS_HUGGINGFACE_API_KEY (preferred) or HUGGINGFACE_API_KEY/HUGGINGFACEHUB_API_TOKEN."
    )


__all__ = ["HuggingFaceProvider"]
