from __future__ import annotations

import json

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.ai.providers.huggingface_provider import HuggingFaceProvider
from namel3ss.runtime.ai.providers.local_runner_provider import LocalRunnerProvider
from namel3ss.runtime.ai.providers.speech_provider import SpeechProvider
from namel3ss.runtime.ai.providers.third_party_provider import ThirdPartyAPIsProvider
from namel3ss.runtime.ai.providers.vision_gen_provider import VisionGenerationProvider


def _payload(mode: str, seed: int) -> str:
    return json.dumps(
        {
            "mode": mode,
            "source": f"fixtures/{mode}.bin",
            "sha256": "a" * 64,
            "seed": seed,
        },
        sort_keys=True,
    )


def test_huggingface_provider_is_deterministic(monkeypatch) -> None:
    monkeypatch.setenv("NAMEL3SS_HUGGINGFACE_API_KEY", "hf_test_key")
    provider = HuggingFaceProvider()
    first = provider.ask(
        model="huggingface:bert-base-uncased",
        system_prompt="Summarize this.",
        user_input="hello world",
    )
    second = provider.ask(
        model="huggingface:bert-base-uncased",
        system_prompt="Summarize this.",
        user_input="hello world",
    )
    assert first.output == second.output


def test_huggingface_provider_missing_key_errors(monkeypatch) -> None:
    monkeypatch.delenv("NAMEL3SS_HUGGINGFACE_API_KEY", raising=False)
    monkeypatch.delenv("HUGGINGFACE_API_KEY", raising=False)
    monkeypatch.delenv("HUGGINGFACEHUB_API_TOKEN", raising=False)
    with pytest.raises(Namel3ssError) as err:
        HuggingFaceProvider().ask(
            model="huggingface:bert-base-uncased",
            system_prompt=None,
            user_input="hello",
        )
    assert "Missing HuggingFace API key" in str(err.value)


def test_local_runner_provider_rejects_non_text_mode() -> None:
    provider = LocalRunnerProvider()
    with pytest.raises(Namel3ssError) as err:
        provider.ask(
            model="local_runner:llama3-8b-q4",
            system_prompt=None,
            user_input=_payload("image", seed=1),
        )
    assert "does not support mode 'image'" in str(err.value)


def test_vision_generation_provider_records_seed() -> None:
    provider = VisionGenerationProvider()
    response = provider.ask(
        model="vision_gen:stable-diffusion",
        system_prompt="Sunset over lake",
        user_input=_payload("image", seed=7),
    )
    assert response.image_id is not None
    assert response.image_url is not None
    assert "seed=7" in str(response.output)


def test_speech_provider_transcribe_and_synthesize() -> None:
    provider = SpeechProvider()
    transcribe = provider.ask(
        model="speech:whisper-base",
        system_prompt="Transcribe this recording.",
        user_input=_payload("audio", seed=11),
    )
    assert transcribe.transcript is not None
    assert transcribe.output == transcribe.transcript

    synth = provider.ask(
        model="speech:coqui-tts",
        system_prompt="Synthesize speech from text.",
        user_input=_payload("audio", seed=11),
    )
    assert synth.audio_id is not None
    assert synth.audio_url is not None


def test_speech_cloud_model_requires_key(monkeypatch) -> None:
    monkeypatch.delenv("NAMEL3SS_SPEECH_API_KEY", raising=False)
    monkeypatch.delenv("SPEECH_API_KEY", raising=False)
    with pytest.raises(Namel3ssError) as err:
        SpeechProvider().ask(
            model="speech:cloud-tts",
            system_prompt="Synthesize this.",
            user_input=_payload("audio", seed=5),
        )
    assert "Missing Speech API key" in str(err.value)


def test_third_party_provider_requires_key(monkeypatch) -> None:
    monkeypatch.delenv("NAMEL3SS_THIRD_PARTY_APIS_KEY", raising=False)
    monkeypatch.delenv("THIRD_PARTY_APIS_KEY", raising=False)
    with pytest.raises(Namel3ssError) as err:
        ThirdPartyAPIsProvider().ask(
            model="third_party_apis:aws-rekognition-labels",
            system_prompt=None,
            user_input=_payload("image", seed=3),
        )
    assert "Missing third-party provider API key" in str(err.value)
