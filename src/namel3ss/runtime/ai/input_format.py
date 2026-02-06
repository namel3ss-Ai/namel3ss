from __future__ import annotations

import hashlib
import io
import wave
from pathlib import Path
from urllib.parse import urlparse

from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.values.normalize import unwrap_text
from namel3ss.utils.numbers import is_number


TEXT_INPUT_MODE = "text"
STRUCTURED_INPUT_MODE = "structured"
IMAGE_INPUT_MODE = "image"
AUDIO_INPUT_MODE = "audio"
STRUCTURED_INPUT_FORMAT = "structured_json_v1"
IMAGE_INPUT_FORMAT = "image_resource_v1"
AUDIO_INPUT_FORMAT = "audio_resource_v1"

_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
_AUDIO_EXTENSIONS = {".wav", ".mp3", ".m4a", ".aac", ".ogg", ".flac"}
_BLOCKED_CONTENT_TERMS = ("nsfw", "explicit", "gore", "sexual")


def prepare_ai_input(
    value: object,
    *,
    mode: str | None,
    line: int | None = None,
    column: int | None = None,
    project_root: str | Path | None = None,
) -> tuple[str, object | None, str]:
    if mode == STRUCTURED_INPUT_MODE:
        _ensure_structured_value(value, line=line, column=column, path=())
        text = canonical_json_dumps(value, pretty=False, drop_run_keys=False)
        return text, value, STRUCTURED_INPUT_FORMAT
    if mode in {IMAGE_INPUT_MODE, AUDIO_INPUT_MODE}:
        return _prepare_multimodal_input(
            value,
            mode=mode,
            line=line,
            column=column,
            project_root=project_root,
        )
    if mode not in (None, TEXT_INPUT_MODE):
        raise Namel3ssError(f"Unknown AI input mode '{mode}'", line=line, column=column)
    text_value = unwrap_text(value)
    if not isinstance(text_value, str):
        raise Namel3ssError("AI input must be a string", line=line, column=column)
    return text_value, None, TEXT_INPUT_MODE


def _ensure_structured_value(
    value: object,
    *,
    line: int | None,
    column: int | None,
    path: tuple[object, ...],
) -> None:
    if value is None or isinstance(value, (str, bool)) or is_number(value):
        return
    if isinstance(value, dict):
        for key, child in value.items():
            _ensure_structured_key(key, line=line, column=column, path=path)
            _ensure_structured_value(child, line=line, column=column, path=path + (str(key),))
        return
    if isinstance(value, list):
        for idx, item in enumerate(value):
            _ensure_structured_value(item, line=line, column=column, path=path + (idx,))
        return
    if isinstance(value, tuple):
        for idx, item in enumerate(value):
            _ensure_structured_value(item, line=line, column=column, path=path + (idx,))
        return
    raise Namel3ssError(
        f"Structured AI input contains an unsupported value{_format_path(path)}.",
        line=line,
        column=column,
    )


def _ensure_structured_key(
    key: object,
    *,
    line: int | None,
    column: int | None,
    path: tuple[object, ...],
) -> None:
    if isinstance(key, (str, bool)) or is_number(key):
        return
    raise Namel3ssError(
        f"Structured AI input map keys must be text, number, or boolean{_format_path(path)}.",
        line=line,
        column=column,
    )


def _format_path(path: tuple[object, ...]) -> str:
    if not path:
        return ""
    parts: list[str] = []
    for item in path:
        if isinstance(item, int):
            parts.append(f"index {item}")
        else:
            parts.append(f"key '{item}'")
    return " at " + " -> ".join(parts)


def _prepare_multimodal_input(
    value: object,
    *,
    mode: str,
    line: int | None,
    column: int | None,
    project_root: str | Path | None,
) -> tuple[str, object | None, str]:
    source, source_kind, source_bytes, seed, metadata = _resolve_multimodal_source(
        value,
        mode=mode,
        line=line,
        column=column,
        project_root=project_root,
    )
    _enforce_content_filter(source, mode=mode, line=line, column=column)
    payload: dict[str, object] = {
        "mode": mode,
        "source": source,
        "source_kind": source_kind,
    }
    payload.update(metadata)
    if source_bytes is not None:
        digest = hashlib.sha256(source_bytes).hexdigest()
        payload["sha256"] = digest
        payload["size_bytes"] = len(source_bytes)
    else:
        digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
        payload["sha256"] = digest
        payload["size_bytes"] = None
    payload["seed"] = _resolve_seed(seed, digest)
    input_format = IMAGE_INPUT_FORMAT if mode == IMAGE_INPUT_MODE else AUDIO_INPUT_FORMAT
    text = canonical_json_dumps(payload, pretty=False, drop_run_keys=False)
    return text, payload, input_format


def _resolve_multimodal_source(
    value: object,
    *,
    mode: str,
    line: int | None,
    column: int | None,
    project_root: str | Path | None,
) -> tuple[str, str, bytes | None, int | None, dict[str, object]]:
    source_seed: int | None = None
    source_value = value
    if isinstance(value, dict):
        for key in ("source", "path", "url", "resource"):
            candidate = value.get(key)
            if isinstance(candidate, str) and candidate.strip():
                source_value = candidate
                break
        source_seed = _as_seed(value.get("seed"), line=line, column=column)
    if source_value is None and mode == IMAGE_INPUT_MODE:
        return "generated_prompt", "generated", None, source_seed, {}
    if isinstance(source_value, (bytes, bytearray)):
        content = bytes(source_value)
        if not content:
            raise Namel3ssError(f"{_mode_label(mode)} input bytes are empty.", line=line, column=column)
        metadata = _extract_content_metadata(content, mode=mode, source="inline_bytes", line=line, column=column)
        return "inline_bytes", "inline_bytes", content, source_seed, metadata
    source_text = unwrap_text(source_value)
    if not isinstance(source_text, str) or not source_text.strip():
        raise Namel3ssError(
            f"{_mode_label(mode)} input must be a file path, URL, or state resource reference.",
            line=line,
            column=column,
        )
    source = source_text.strip()
    parsed = urlparse(source)
    if parsed.scheme in {"http", "https"}:
        _validate_url_extension(source, mode=mode, line=line, column=column)
        return source, "url", None, source_seed, {}
    target = _resolve_local_path(source, project_root=project_root)
    if not target.exists():
        raise Namel3ssError(f"{_mode_label(mode)} input file not found: {target}", line=line, column=column)
    try:
        content = target.read_bytes()
    except OSError as err:
        raise Namel3ssError(f"{_mode_label(mode)} input file cannot be read: {target}", line=line, column=column) from err
    if not content:
        raise Namel3ssError(f"{_mode_label(mode)} input file is empty: {target}", line=line, column=column)
    _validate_file_extension(target, mode=mode, line=line, column=column)
    metadata = _extract_content_metadata(content, mode=mode, source=str(target), line=line, column=column)
    return str(target), "file_path", content, source_seed, metadata


def _resolve_local_path(source: str, *, project_root: str | Path | None) -> Path:
    raw = Path(source)
    if raw.is_absolute():
        return raw
    root = Path(project_root) if project_root else Path.cwd()
    return (root / raw).resolve()


def _validate_file_extension(path: Path, *, mode: str, line: int | None, column: int | None) -> None:
    extension = path.suffix.lower()
    _validate_extension(extension, mode=mode, line=line, column=column)


def _validate_url_extension(url: str, *, mode: str, line: int | None, column: int | None) -> None:
    extension = Path(urlparse(url).path).suffix.lower()
    if extension:
        _validate_extension(extension, mode=mode, line=line, column=column)


def _validate_extension(extension: str, *, mode: str, line: int | None, column: int | None) -> None:
    allowed = _IMAGE_EXTENSIONS if mode == IMAGE_INPUT_MODE else _AUDIO_EXTENSIONS
    if extension in allowed:
        return
    allowed_text = ", ".join(sorted(allowed))
    raise Namel3ssError(
        f"{_mode_label(mode)} input extension '{extension or '<none>'}' is unsupported. Use one of: {allowed_text}.",
        line=line,
        column=column,
    )


def _extract_content_metadata(
    content: bytes,
    *,
    mode: str,
    source: str,
    line: int | None,
    column: int | None,
) -> dict[str, object]:
    if mode == IMAGE_INPUT_MODE:
        _validate_image_signature(content, source=source, line=line, column=column)
        width, height = _image_dimensions(content)
        if width is None or height is None:
            return {"image_resolution": None}
        return {"image_resolution": {"width": width, "height": height}}
    _validate_audio_signature(content, source=source, line=line, column=column)
    duration_ms = _audio_duration_ms(content)
    return {"audio_duration_ms": duration_ms}


def _validate_image_signature(content: bytes, *, source: str, line: int | None, column: int | None) -> None:
    checks = (
        content.startswith(b"\x89PNG\r\n\x1a\n"),
        content.startswith(b"\xff\xd8"),
        content.startswith(b"GIF8"),
        content.startswith(b"BM"),
        len(content) > 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP",
    )
    if any(checks):
        return
    raise Namel3ssError(f"Image input could not be decoded: {source}", line=line, column=column)


def _validate_audio_signature(content: bytes, *, source: str, line: int | None, column: int | None) -> None:
    checks = (
        content.startswith(b"RIFF") and b"WAVE" in content[:16],
        content.startswith(b"ID3"),
        content[:2] in {b"\xff\xf1", b"\xff\xf9", b"\xff\xfb"},
        content.startswith(b"OggS"),
        content.startswith(b"fLaC"),
        len(content) > 12 and content[4:8] == b"ftyp",
    )
    if any(checks):
        return
    raise Namel3ssError(f"Audio input could not be decoded: {source}", line=line, column=column)


def _audio_duration_ms(content: bytes) -> int | None:
    if not (content.startswith(b"RIFF") and b"WAVE" in content[:16]):
        return None
    try:
        with wave.open(io.BytesIO(content), "rb") as wav_reader:
            frames = wav_reader.getnframes()
            rate = wav_reader.getframerate()
            if rate <= 0:
                return None
            duration_ms = int((frames / rate) * 1000)
            return duration_ms if duration_ms >= 0 else None
    except Exception:
        return None


def _image_dimensions(content: bytes) -> tuple[int | None, int | None]:
    if content.startswith(b"\x89PNG\r\n\x1a\n") and len(content) >= 24:
        width = int.from_bytes(content[16:20], "big")
        height = int.from_bytes(content[20:24], "big")
        return width, height
    if content.startswith(b"GIF8") and len(content) >= 10:
        width = int.from_bytes(content[6:8], "little")
        height = int.from_bytes(content[8:10], "little")
        return width, height
    if content.startswith(b"BM") and len(content) >= 26:
        width = int.from_bytes(content[18:22], "little", signed=True)
        height = int.from_bytes(content[22:26], "little", signed=True)
        if width > 0 and height != 0:
            return width, abs(height)
    return None, None


def _resolve_seed(seed: int | None, digest: str) -> int:
    if seed is not None:
        return seed
    return int(digest[:8], 16)


def _as_seed(value: object, *, line: int | None, column: int | None) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise Namel3ssError("Multimodal seed must be an integer.", line=line, column=column)
    if value < 0:
        raise Namel3ssError("Multimodal seed must be a non-negative integer.", line=line, column=column)
    return value


def _enforce_content_filter(value: str, *, mode: str, line: int | None, column: int | None) -> None:
    lowered = value.lower()
    for token in _BLOCKED_CONTENT_TERMS:
        if token in lowered:
            raise Namel3ssError(
                f"{_mode_label(mode)} input blocked by content filter ({token}).",
                line=line,
                column=column,
            )


def _mode_label(mode: str) -> str:
    if mode == IMAGE_INPUT_MODE:
        return "Image"
    if mode == AUDIO_INPUT_MODE:
        return "Audio"
    return "AI"


__all__ = [
    "AUDIO_INPUT_FORMAT",
    "AUDIO_INPUT_MODE",
    "IMAGE_INPUT_FORMAT",
    "IMAGE_INPUT_MODE",
    "STRUCTURED_INPUT_FORMAT",
    "STRUCTURED_INPUT_MODE",
    "TEXT_INPUT_MODE",
    "prepare_ai_input",
]
