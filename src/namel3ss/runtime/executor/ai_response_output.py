from __future__ import annotations


def extract_response_text(response: object) -> object:
    if not hasattr(response, "output"):
        return response
    output = getattr(response, "output")
    if isinstance(output, str) and output.strip():
        return output
    if output not in (None, ""):
        return output
    for field in ("transcript", "description", "image_url", "audio_url", "image_id", "audio_id"):
        value = getattr(response, field, None)
        if isinstance(value, str) and value.strip():
            return value
    return output


__all__ = ["extract_response_text"]
