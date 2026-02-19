from __future__ import annotations

from namel3ss.ingestion.extract_text_utils import normalize_extracted_text


def decode_pdf_string(raw: bytes) -> str:
    output = bytearray()
    idx = 0
    while idx < len(raw):
        char = raw[idx]
        if char == 92:  # backslash
            idx += 1
            if idx >= len(raw):
                break
            esc = raw[idx]
            if esc in b"nrtbf":
                output.extend({"n": b"\n", "r": b"\r", "t": b"\t", "b": b"\b", "f": b"\f"}[chr(esc)])
            elif esc in b"\\()":
                output.append(esc)
            elif 48 <= esc <= 55:
                octal = bytes([esc])
                for _ in range(2):
                    if idx + 1 < len(raw) and 48 <= raw[idx + 1] <= 55:
                        idx += 1
                        octal += bytes([raw[idx]])
                    else:
                        break
                try:
                    output.append(int(octal, 8))
                except Exception:
                    pass
            else:
                output.append(esc)
        else:
            output.append(char)
        idx += 1
    return decode_pdf_payload(bytes(output))


def decode_pdf_hex_string(raw: bytes) -> str:
    if not raw:
        return ""
    compact = b"".join(raw.split())
    if not compact:
        return ""
    if len(compact) % 2:
        compact += b"0"
    try:
        payload = bytes.fromhex(compact.decode("ascii"))
    except Exception:
        return ""
    return decode_pdf_payload(payload)


def decode_pdf_payload(payload: bytes) -> str:
    if not payload:
        return ""
    try:
        if payload.startswith(b"\xfe\xff") or payload.startswith(b"\xff\xfe"):
            return normalize_extracted_text(payload.decode("utf-16", errors="ignore"))
    except Exception:
        pass
    if payload.count(b"\x00") * 2 >= len(payload):
        try:
            return normalize_extracted_text(payload.decode("utf-16-be", errors="ignore"))
        except Exception:
            return ""
    try:
        return normalize_extracted_text(payload.decode("utf-8"))
    except Exception:
        pass
    for encoding in ("cp1252", "latin-1"):
        try:
            decoded = payload.decode(encoding, errors="ignore")
        except Exception:
            continue
        return normalize_extracted_text(decoded)
    return ""


def is_probable_text_stream(payload: bytes) -> bool:
    if not payload:
        return False
    if b"BT" in payload and b"ET" in payload:
        return True
    if b"Tj" in payload or b"TJ" in payload:
        return True
    sample = payload[:4096]
    if not sample:
        return False
    control = 0
    for value in sample:
        if value == 0:
            control += 1
            continue
        if value < 9:
            control += 1
            continue
        if 14 <= value < 32:
            control += 1
            continue
        if value == 127:
            control += 1
    return control <= len(sample) // 8


def looks_like_readable_text(text: str) -> bool:
    if not text:
        return False
    cleaned = "".join(ch for ch in text if ch in {"\n", "\t", " "} or ord(ch) >= 32).strip()
    if len(cleaned) < 2:
        return False
    alnum = sum(1 for ch in cleaned if ch.isalnum())
    return alnum > 0


__all__ = [
    "decode_pdf_hex_string",
    "decode_pdf_payload",
    "decode_pdf_string",
    "is_probable_text_stream",
    "looks_like_readable_text",
]
