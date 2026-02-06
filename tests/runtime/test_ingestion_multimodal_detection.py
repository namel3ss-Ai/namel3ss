from __future__ import annotations

import io
import wave

from namel3ss.ingestion.detect import detect_upload


def _png_bytes() -> bytes:
    return (
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\rIHDR"
        b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00"
        b"\x1f\x15\xc4\x89"
        b"\x00\x00\x00\x0cIDAT\x08\x99c```\x00\x00\x00\x04\x00\x01"
        b"\x0d\n-\xb4"
        b"\x00\x00\x00\x00IEND\xaeB`\x82"
    )


def _wav_bytes() -> bytes:
    with io.BytesIO() as stream:
        with wave.open(stream, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(8000)
            wav_file.writeframes(b"\x00\x00" * 8000)
        return stream.getvalue()


def test_detect_upload_reports_image_resolution() -> None:
    detected = detect_upload(
        {"name": "photo.png", "content_type": "image/png"},
        content=_png_bytes(),
    )
    assert detected["type"] == "image"
    assert detected["image_resolution"] == {"width": 1, "height": 1}
    assert detected["audio_duration_ms"] is None


def test_detect_upload_reports_audio_duration() -> None:
    detected = detect_upload(
        {"name": "note.wav", "content_type": "audio/wav"},
        content=_wav_bytes(),
    )
    assert detected["type"] == "audio"
    assert detected["audio_duration_ms"] == 1000
    assert detected["image_resolution"] is None
