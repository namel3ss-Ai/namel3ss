import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.providers.pack_registry import (
    capability_for_provider,
    get_provider_metadata,
    model_supports_mode,
    provider_name_for_model,
    provider_pack_names,
    validate_model_identifier,
)


def test_provider_pack_names_are_stable() -> None:
    assert provider_pack_names() == (
        "huggingface",
        "local_runner",
        "speech",
        "third_party_apis",
        "vision_gen",
    )


def test_provider_metadata_contract() -> None:
    metadata = get_provider_metadata("vision_gen")
    assert metadata is not None
    assert metadata.capability_token == "vision_gen"
    assert metadata.supported_modes == ("image",)
    assert metadata.has_model("vision_gen:stable-diffusion")
    assert capability_for_provider("vision_gen") == "vision_gen"


def test_provider_name_for_model_prefix() -> None:
    assert provider_name_for_model("huggingface:bert-base-uncased") == "huggingface"
    assert provider_name_for_model("unknown:model") is None
    assert provider_name_for_model("plain-model-name") is None


def test_validate_model_identifier_rejects_unknown_model() -> None:
    with pytest.raises(Namel3ssError) as err:
        validate_model_identifier(
            model_identifier="vision_gen:does-not-exist",
            provider_name="vision_gen",
        )
    assert "Unknown model" in str(err.value)


def test_model_supports_mode_for_provider_packs() -> None:
    assert model_supports_mode(model_identifier="local_runner:llama3-8b-q4", mode="text") is True
    assert model_supports_mode(model_identifier="local_runner:llama3-8b-q4", mode="image") is False
    assert model_supports_mode(model_identifier="speech:whisper-base", mode="audio") is True
    assert model_supports_mode(model_identifier="speech:whisper-base", mode="image") is False
