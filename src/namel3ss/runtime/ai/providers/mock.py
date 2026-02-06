from __future__ import annotations

import json

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
            if isinstance(resp, AIResponse):
                return resp
        multimodal = _build_multimodal_response(model=model, system_prompt=system_prompt, user_input=user_input)
        if multimodal is not None:
            return multimodal
        prefix = f"[{model}]"
        mem_note = ""
        if memory:
            mem_note = f" | mem:st={len(memory.get('short_term', []))}"
        if system_prompt:
            return AIResponse(output=str(f"{prefix} {system_prompt} :: {user_input}{mem_note}"))
        return AIResponse(output=str(f"{prefix} {user_input}{mem_note}"))


def _build_multimodal_response(*, model: str, system_prompt: str | None, user_input: str) -> AIResponse | None:
    payload = _parse_input_payload(user_input)
    if payload is None:
        return None
    mode = payload.get("mode")
    if mode == "image":
        return _build_image_response(model=model, system_prompt=system_prompt, payload=payload)
    if mode == "audio":
        return _build_audio_response(model=model, system_prompt=system_prompt, payload=payload)
    return None


def _parse_input_payload(user_input: str) -> dict[str, object] | None:
    if not isinstance(user_input, str):
        return None
    stripped = user_input.strip()
    if not stripped.startswith("{"):
        return None
    try:
        payload = json.loads(stripped)
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    mode = payload.get("mode")
    if mode not in {"image", "audio"}:
        return None
    return payload


def _build_image_response(*, model: str, system_prompt: str | None, payload: dict[str, object]) -> AIResponse:
    source = _payload_source(payload)
    digest = str(payload.get("sha256") or "")
    prompt = f"{(system_prompt or '').lower()} {model.lower()}"
    if "classif" in prompt or "label" in prompt:
        label = _deterministic_label(digest)
        text = f"{label}"
        return AIResponse(output=text, description=text)
    if "generate" in prompt or "draw" in prompt or "create image" in prompt:
        image_id = digest[:16] or "generated"
        image_url = f"mock://image/{image_id}.png"
        text = f"Generated image for {source}"
        return AIResponse(output=text, image_id=image_id, image_url=image_url, description=text)
    resolution = payload.get("image_resolution")
    if isinstance(resolution, dict):
        width = resolution.get("width")
        height = resolution.get("height")
        if isinstance(width, int) and isinstance(height, int):
            text = f"Image caption: {source} ({width}x{height})"
            return AIResponse(output=text, description=text)
    text = f"Image caption: {source}"
    return AIResponse(output=text, description=text)


def _build_audio_response(*, model: str, system_prompt: str | None, payload: dict[str, object]) -> AIResponse:
    source = _payload_source(payload)
    digest = str(payload.get("sha256") or "")
    prompt = f"{(system_prompt or '').lower()} {model.lower()}"
    if "text-to-speech" in prompt or "synth" in prompt or "tts" in prompt:
        audio_id = digest[:16] or "synth"
        audio_url = f"mock://audio/{audio_id}.wav"
        transcript = f"Synthesized audio for {source}"
        return AIResponse(output=transcript, transcript=transcript, audio_url=audio_url)
    transcript = f"Transcript: {digest[:24] or source}"
    return AIResponse(output=transcript, transcript=transcript)


def _payload_source(payload: dict[str, object]) -> str:
    source = payload.get("source")
    if isinstance(source, str) and source.strip():
        return source
    return "unknown"


def _deterministic_label(digest: str) -> str:
    labels = ("chart", "invoice", "receipt", "person", "landscape", "diagram")
    if not digest:
        return labels[0]
    index = int(digest[:8], 16) % len(labels)
    return labels[index]
