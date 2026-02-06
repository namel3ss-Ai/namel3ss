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


class ThirdPartyAPIsProvider(AIProvider):
    def ask(self, *, model: str, system_prompt: str | None, user_input: str, tools=None, memory=None, tool_results=None):
        _resolve_third_party_key()
        mode = input_mode(user_input)
        ensure_mode_supported(provider="third_party_apis", mode=mode, allowed=("image", "audio"))
        seed = payload_seed(user_input)
        digest = digest_for_call(
            provider="third_party_apis",
            model=model,
            system_prompt=system_prompt,
            user_input=user_input,
            seed=seed,
        )
        model_name = model.split(":", 1)[-1]
        if mode == "image":
            label = deterministic_label(digest, ("product", "vehicle", "document", "face"))
            text = f"third_party_apis:{model_name} image label={label}"
            return AIResponse(output=text, description=text)
        transcript = f"third_party_apis:{model_name} transcript:{digest[:24]}"
        return AIResponse(output=transcript, transcript=transcript)


def _resolve_third_party_key() -> str:
    preferred = read_env("NAMEL3SS_THIRD_PARTY_APIS_KEY")
    if preferred is not None and str(preferred).strip() != "":
        return require_env("third_party_apis", "NAMEL3SS_THIRD_PARTY_APIS_KEY", preferred)
    alias = read_env("THIRD_PARTY_APIS_KEY")
    if alias is not None and str(alias).strip() != "":
        return require_env("third_party_apis", "THIRD_PARTY_APIS_KEY", alias)
    raise Namel3ssError(
        "Missing third-party provider API key. Set NAMEL3SS_THIRD_PARTY_APIS_KEY (preferred) or THIRD_PARTY_APIS_KEY."
    )


__all__ = ["ThirdPartyAPIsProvider"]
