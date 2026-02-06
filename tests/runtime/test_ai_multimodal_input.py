from __future__ import annotations

import io
import json
import wave
from pathlib import Path

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.ai.providers.mock import MockProvider
from namel3ss.runtime.executor import Executor
from namel3ss.pipelines.registry import pipeline_contracts
from tests.conftest import lower_ir_program


def _write_png(path: Path) -> None:
    # 1x1 deterministic PNG.
    data = (
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\rIHDR"
        b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00"
        b"\x1f\x15\xc4\x89"
        b"\x00\x00\x00\x0cIDAT\x08\x99c```\x00\x00\x00\x04\x00\x01"
        b"\x0d\n-\xb4"
        b"\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    path.write_bytes(data)


def _write_wav(path: Path) -> None:
    with io.BytesIO() as stream:
        with wave.open(stream, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(8000)
            wav_file.writeframes(b"\x00\x00" * 8000)
        path.write_bytes(stream.getvalue())


def _run_flow(source: str, *, initial_state: dict | None = None, project_root: Path | None = None):
    program = lower_ir_program(source)
    flow = program.flows[0]
    schemas = {schema.name: schema for schema in program.records}
    executor = Executor(
        flow,
        schemas=schemas,
        initial_state=initial_state,
        ai_profiles=program.ais,
        agents=program.agents,
        tools=program.tools,
        functions=program.functions,
        flows={entry.name: entry for entry in program.flows},
        flow_contracts=getattr(program, "flow_contracts", {}) or {},
        pipeline_contracts=pipeline_contracts(),
        capabilities=getattr(program, "capabilities", ()),
        project_root=project_root,
        app_path=(project_root / "app.ai").as_posix() if project_root is not None else None,
    )
    return executor.run()


def test_image_input_is_deterministic(tmp_path: Path) -> None:
    image_path = tmp_path / "image.png"
    _write_png(image_path)
    source = f'''spec is "1.0"

capabilities:
  vision

ai "assistant":
  provider is "mock"
  model is "vision-classifier"
  system_prompt is "Classify the image."

flow "demo":
  ask ai "assistant" with image input: state.image_path as reply
  return reply
'''
    first = _run_flow(source, initial_state={"image_path": str(image_path)}, project_root=tmp_path)
    second = _run_flow(source, initial_state={"image_path": str(image_path)}, project_root=tmp_path)
    assert first.last_value == second.last_value
    trace = first.traces[0]
    assert trace.input_format == "image_resource_v1"
    assert trace.input_structured["mode"] == "image"
    assert isinstance(trace.input_structured["seed"], int)


def test_audio_input_is_deterministic(tmp_path: Path) -> None:
    audio_path = tmp_path / "note.wav"
    _write_wav(audio_path)
    source = f'''spec is "1.0"

capabilities:
  speech

ai "assistant":
  provider is "mock"
  model is "speech-to-text"
  system_prompt is "Transcribe this audio."

flow "demo":
  ask ai "assistant" with audio input: state.audio_path as reply
  return reply
'''
    first = _run_flow(source, initial_state={"audio_path": str(audio_path)}, project_root=tmp_path)
    second = _run_flow(source, initial_state={"audio_path": str(audio_path)}, project_root=tmp_path)
    assert first.last_value == second.last_value
    assert str(first.last_value).startswith("Transcript:")
    trace = first.traces[0]
    assert trace.input_format == "audio_resource_v1"
    assert trace.input_structured["mode"] == "audio"
    assert trace.input_structured["audio_duration_ms"] == 1000


def test_missing_image_file_is_reported(tmp_path: Path) -> None:
    source = '''spec is "1.0"

capabilities:
  vision

ai "assistant":
  provider is "mock"
  model is "vision-model"

flow "demo":
  ask ai "assistant" with image input: state.image_path as reply
  return reply
'''
    with pytest.raises(Namel3ssError) as excinfo:
        _run_flow(
            source,
            initial_state={"image_path": str(tmp_path / "missing.png")},
            project_root=tmp_path,
        )
    assert "input file not found" in str(excinfo.value)


def test_content_filter_blocks_flagged_multimodal_url(tmp_path: Path) -> None:
    source = '''spec is "1.0"

capabilities:
  vision

ai "assistant":
  provider is "mock"
  model is "vision-model"

flow "demo":
  ask ai "assistant" with image input: "https://example.com/nsfw.png" as reply
  return reply
'''
    with pytest.raises(Namel3ssError) as excinfo:
        _run_flow(source, project_root=tmp_path)
    assert "blocked by content filter" in str(excinfo.value)


def test_mock_provider_multimodal_modes() -> None:
    provider = MockProvider()
    image_payload = json.dumps(
        {
            "mode": "image",
            "source": "assets/photo.png",
            "sha256": "a" * 64,
            "seed": 7,
        },
        sort_keys=True,
    )
    classify = provider.ask(
        model="vision-classifier",
        system_prompt="Classify this image.",
        user_input=image_payload,
    )
    assert classify.output in {"chart", "invoice", "receipt", "person", "landscape", "diagram"}

    generate = provider.ask(
        model="image-generator",
        system_prompt="Generate image.",
        user_input=image_payload,
    )
    assert generate.image_url is not None
    assert generate.image_id is not None
    assert isinstance(generate.output, str) and generate.output

    audio_payload = json.dumps(
        {
            "mode": "audio",
            "source": "assets/note.wav",
            "sha256": "b" * 64,
            "seed": 9,
        },
        sort_keys=True,
    )
    transcript = provider.ask(
        model="speech-to-text",
        system_prompt="Transcribe this audio.",
        user_input=audio_payload,
    )
    assert transcript.transcript is not None
    assert transcript.output == transcript.transcript

    synthesis = provider.ask(
        model="text-to-speech",
        system_prompt="Synthesize speech from text.",
        user_input=audio_payload,
    )
    assert synthesis.audio_url is not None
