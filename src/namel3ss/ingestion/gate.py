from __future__ import annotations


def gate_quality(signals: dict) -> tuple[str, list[str]]:
    reasons: list[str] = []
    text_chars = int(signals.get("text_chars") or 0)
    unique_token_ratio = float(signals.get("unique_token_ratio") or 0)
    non_ascii_ratio = float(signals.get("non_ascii_ratio") or 0)
    repeated_line_ratio = float(signals.get("repeated_line_ratio") or 0)
    table_like_ratio = float(signals.get("table_like_ratio") or 0)
    empty_pages_ratio = float(signals.get("empty_pages_ratio") or 0)
    uppercase_alpha_ratio = float(signals.get("uppercase_alpha_ratio") or 0)
    vowel_alpha_ratio = float(signals.get("vowel_alpha_ratio") or 0)
    unreadable_text_pattern = (
        text_chars >= 80
        and uppercase_alpha_ratio >= 0.9
        and vowel_alpha_ratio <= 0.22
    )

    if text_chars < 20:
        reasons.append("text_too_short")
    if unique_token_ratio < 0.2:
        reasons.append("low_unique_tokens")
    if non_ascii_ratio > 0.5:
        reasons.append("high_non_ascii")
    if repeated_line_ratio > 0.5:
        reasons.append("repeated_lines")
    if table_like_ratio > 0.6:
        reasons.append("table_heavy")
    if empty_pages_ratio > 0.5:
        reasons.append("many_empty_pages")
    if unreadable_text_pattern:
        reasons.append("unreadable_text_pattern")

    if text_chars == 0:
        return "block", reasons or ["empty_text"]
    if unreadable_text_pattern:
        return "block", reasons
    if text_chars < 50 or unique_token_ratio < 0.1 or non_ascii_ratio > 0.8 or repeated_line_ratio > 0.7:
        return "block", reasons
    if reasons:
        return "warn", reasons
    return "pass", []


def should_fallback(signals: dict, detected: dict) -> bool:
    kind = str(detected.get("type") or "")
    if kind == "pdf":
        text_chars = int(signals.get("text_chars") or 0)
        empty_pages_ratio = float(signals.get("empty_pages_ratio") or 0)
        return text_chars < 200 or empty_pages_ratio > 0.5
    if kind == "image":
        text_chars = int(signals.get("text_chars") or 0)
        return text_chars == 0
    return False


__all__ = ["gate_quality", "should_fallback"]
