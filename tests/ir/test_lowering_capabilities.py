import pytest

from namel3ss.errors.base import Namel3ssError
from tests.conftest import lower_ir_program


def test_missing_http_capability_rejected() -> None:
    source = '''spec is "1.0"

tool "fetch":
  implemented using http

  input:
    url is text

  output:
    status is number

flow "demo":
  let response is fetch:
    url is "https://example.com"
  return response
'''
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "Missing capabilities" in exc.value.message


def test_missing_jobs_capability_rejected() -> None:
    source = '''spec is "1.0"

job "refresh":
  return "ok"

flow "demo":
  return "ok"
'''
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "Missing capabilities" in exc.value.message


def test_capabilities_allow_http_and_jobs() -> None:
    source = '''spec is "1.0"

capabilities:
  jobs
  http

tool "fetch":
  implemented using http

  input:
    url is text

  output:
    status is number

job "refresh":
  return "ok"

flow "demo":
  enqueue job "refresh"
  let response is fetch:
    url is "https://example.com"
  return response
'''
    program = lower_ir_program(source)
    assert program.capabilities == ("http", "jobs")


def test_missing_vision_capability_rejected() -> None:
    source = '''spec is "1.0"

ai "assistant":
  provider is "mock"
  model is "vision-model"

flow "demo":
  ask ai "assistant" with image input: "assets/photo.png" as reply
  return reply
'''
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "Missing capabilities" in exc.value.message
    assert "vision" in exc.value.message


def test_missing_speech_capability_rejected() -> None:
    source = '''spec is "1.0"

ai "assistant":
  provider is "mock"
  model is "speech-model"

flow "demo":
  ask ai "assistant" with audio input: "assets/note.wav" as reply
  return reply
'''
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "Missing capabilities" in exc.value.message
    assert "speech" in exc.value.message


def test_provider_without_vision_support_rejected() -> None:
    source = '''spec is "1.0"

capabilities:
  vision

ai "assistant":
  provider is "ollama"
  model is "llama3"

flow "demo":
  ask ai "assistant" with image input: "assets/photo.png" as reply
  return reply
'''
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "does not support image input mode" in exc.value.message


def test_provider_pack_capability_is_required() -> None:
    source = '''spec is "1.0"

ai "assistant":
  model is "huggingface:bert-base-uncased"

flow "demo":
  ask ai "assistant" with input: "hello" as reply
  return reply
'''
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "Missing capabilities" in exc.value.message
    assert "huggingface" in exc.value.message


def test_provider_pack_model_mode_mismatch_rejected() -> None:
    source = '''spec is "1.0"

capabilities:
  local_runner
  vision

ai "assistant":
  provider is "local_runner"
  model is "local_runner:llama3-8b-q4"

flow "demo":
  ask ai "assistant" with image input: "assets/photo.png" as reply
  return reply
'''
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "does not support image mode" in exc.value.message


def test_missing_streaming_capability_rejected() -> None:
    source = '''spec is "1.0"

ai "assistant":
  provider is "mock"
  model is "mock-model"

flow "demo":
  ask ai "assistant" with stream: true and input: "hello" as reply
  return reply
'''
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "Missing capabilities" in exc.value.message
    assert "streaming" in exc.value.message


def test_provider_without_streaming_support_rejected() -> None:
    source = '''spec is "1.0"

capabilities:
  streaming

ai "assistant":
  provider is "ollama"
  model is "llama3"

flow "demo":
  ask ai "assistant" with stream: true and input: "hello" as reply
  return reply
'''
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "does not support stream=true" in exc.value.message


def test_custom_ui_capability_required_for_plugins(monkeypatch, tmp_path) -> None:
    plugin_root = tmp_path / "ui_plugins"
    sample = plugin_root / "charts"
    sample.mkdir(parents=True)
    (sample / "plugin.yaml").write_text(
        """
name: charts
module: render.py
components:
  - name: LineChart
    props:
      data: state_path
      x_field: string
      y_field: string
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (sample / "render.py").write_text(
        """
def render(props, state):
    return [{"type": "line_chart", "props": props}]
""".strip()
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("N3_UI_PLUGIN_DIRS", str(plugin_root))
    source = '''spec is "1.0"

use plugin "charts"

page "home":
  LineChart data: state.metrics.records x_field: "month" y_field: "revenue"
'''
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "Missing capabilities: custom_ui." in exc.value.message
