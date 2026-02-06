from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.ai.provider import AIProvider, AIResponse
from namel3ss.runtime.ai.providers._shared.errors import require_env
from namel3ss.runtime.ai.providers.provider_pack_support import digest_for_call, ensure_mode_supported, input_mode, payload_seed
from namel3ss.security import read_env


class SpeechProvider(AIProvider):
    def ask(self, *, model: str, system_prompt: str | None, user_input: str, tools=None, memory=None, tool_results=None):
        mode = input_mode(user_input)
        ensure_mode_supported(provider="speech", mode=mode, allowed=("audio",))
        model_name = model.split(":", 1)[-1]
        if model_name == "cloud-tts":
            _resolve_speech_key()
        seed = payload_seed(user_input)
        digest = digest_for_call(
            provider="speech",
            model=model,
            system_prompt=system_prompt,
            user_input=user_input,
            seed=seed,
        )
        lowered_prompt = (system_prompt or "").lower()
        if "synth" in lowered_prompt or "tts" in lowered_prompt or model_name == "coqui-tts":
            audio_id = digest[:16]
            audio_url = f"speech://audio/{audio_id}.wav"
            transcript = f"speech synthesis ready ({audio_id})"
            return AIResponse(output=transcript, transcript=transcript, audio_url=audio_url, audio_id=audio_id)
        transcript = f"speech transcript:{digest[:24]}"
        return AIResponse(output=transcript, transcript=transcript)


def _resolve_speech_key() -> str:
    preferred = read_env("NAMEL3SS_SPEECH_API_KEY")
    if preferred is not None and str(preferred).strip() != "":
        return require_env("speech", "NAMEL3SS_SPEECH_API_KEY", preferred)
    alias = read_env("SPEECH_API_KEY")
    if alias is not None and str(alias).strip() != "":
        return require_env("speech", "SPEECH_API_KEY", alias)
    raise Namel3ssError(
        "Missing Speech API key. Set NAMEL3SS_SPEECH_API_KEY (preferred) or SPEECH_API_KEY."
    )


__all__ = ["SpeechProvider"]
